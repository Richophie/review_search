-- Partner marketplace isolated schema. Review and apply via Supabase migration tooling.
-- NEVER run against production without backup and RLS review.
create table if not exists public.partner_profiles (
  user_id uuid primary key references auth.users(id) on delete cascade,
  display_name text not null check (length(trim(display_name)) between 1 and 60),
  role text not null check (role in ('advertiser','creator')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create table if not exists public.partner_organizations (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null references auth.users(id),
  name text not null check (length(trim(name)) between 1 and 120),
  created_at timestamptz not null default now(),
  unique (id, owner_id)
);
create table if not exists public.partner_creator_channels (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null references auth.users(id) on delete cascade,
  platform text not null check (platform in ('naver_blog','instagram','youtube','tiktok','other')),
  channel_url text not null check (length(channel_url) between 8 and 2048),
  created_at timestamptz not null default now()
);
create table if not exists public.partner_campaigns (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references public.partner_organizations(id),
  owner_id uuid not null references auth.users(id),
  title text not null check (length(trim(title)) between 5 and 150),
  description text not null default '',
  benefit text not null default '',
  category text not null default '기타',
  region text,
  slots integer not null check (slots between 1 and 1000),
  apply_deadline timestamptz not null,
  status text not null default 'draft' check (status in ('draft','pending_review','recruiting','selection','experience','review','completed','cancelled','suspended')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  foreign key (organization_id, owner_id) references public.partner_organizations(id,owner_id)
);
create table if not exists public.partner_applications (
  id uuid primary key default gen_random_uuid(),
  campaign_id uuid not null references public.partner_campaigns(id),
  creator_id uuid not null references auth.users(id) on delete cascade,
  message text not null default '' check (length(message) <= 2000),
  status text not null default 'applied' check (status in ('applied','selected','rejected','withdrawn','cancelled')),
  applied_at timestamptz not null default now(),
  unique (campaign_id,creator_id)
);
create index if not exists partner_campaigns_public_idx on public.partner_campaigns(status,apply_deadline);
create index if not exists partner_campaigns_owner_idx on public.partner_campaigns(owner_id);
create index if not exists partner_applications_campaign_idx on public.partner_applications(campaign_id,status);

alter table public.partner_profiles enable row level security;
alter table public.partner_organizations enable row level security;
alter table public.partner_creator_channels enable row level security;
alter table public.partner_campaigns enable row level security;
alter table public.partner_applications enable row level security;

create policy "partner profile self read" on public.partner_profiles for select to authenticated using (user_id = (select auth.uid()));
create policy "partner profile self update" on public.partner_profiles for update to authenticated using (user_id = (select auth.uid())) with check (user_id = (select auth.uid()));
-- No client insert into profile; handled by trigger below.
create policy "partner organization owner read" on public.partner_organizations for select to authenticated using (owner_id = (select auth.uid()));
create policy "partner organization owner insert" on public.partner_organizations for insert to authenticated with check (owner_id = (select auth.uid()) and exists (select 1 from public.partner_profiles p where p.user_id = auth.uid() and p.role = 'advertiser'));
create policy "partner organization owner update" on public.partner_organizations for update to authenticated using (owner_id = (select auth.uid())) with check (owner_id = (select auth.uid()));
create policy "partner channels self read" on public.partner_creator_channels for select to authenticated using (owner_id = (select auth.uid()));
create policy "partner channels self insert" on public.partner_creator_channels for insert to authenticated with check (owner_id = (select auth.uid()) and exists (select 1 from public.partner_profiles p where p.user_id = auth.uid() and p.role = 'creator'));
create policy "partner channels self update" on public.partner_creator_channels for update to authenticated using (owner_id = (select auth.uid())) with check (owner_id = (select auth.uid()));
create policy "partner campaigns public or owner read" on public.partner_campaigns for select to anon,authenticated using (status = 'recruiting' or owner_id = (select auth.uid()));
create policy "partner campaigns owner create" on public.partner_campaigns for insert to authenticated with check (
  owner_id = (select auth.uid()) and status = 'draft' and exists (
    select 1 from public.partner_organizations o where o.id=organization_id and o.owner_id=auth.uid()
  )
);
-- No direct client campaign UPDATE: approval/state transitions require server-side workflow.
create policy "partner applications creator or advertiser read" on public.partner_applications for select to authenticated using (
  creator_id = (select auth.uid()) or exists (
    select 1 from public.partner_campaigns c where c.id=campaign_id and c.owner_id=auth.uid()
  )
);
create policy "partner applications creator apply" on public.partner_applications for insert to authenticated with check (
  creator_id = (select auth.uid()) and status='applied'
  and exists(select 1 from public.partner_profiles p where p.user_id=auth.uid() and p.role='creator')
  and exists (select 1 from public.partner_campaigns c where c.id=campaign_id and c.status='recruiting' and c.apply_deadline>now())
);
-- No direct client application UPDATE. Selection requires atomic server-side transaction.

create or replace function public.partner_create_profile_for_user()
returns trigger language plpgsql security definer set search_path = '' as $$
declare requested text;
begin
  requested := new.raw_user_meta_data->>'requested_role';
  if requested not in ('advertiser','creator') then requested := 'creator'; end if;
  insert into public.partner_profiles (user_id,display_name,role)
  values (new.id, coalesce(nullif(left(trim(new.raw_user_meta_data->>'display_name'),60),''),'회원'),requested)
  on conflict (user_id) do nothing;
  return new;
end;
$$;
drop trigger if exists partner_auth_user_created on auth.users;
create trigger partner_auth_user_created after insert on auth.users
for each row execute function public.partner_create_profile_for_user();

-- IMPORTANT SECURITY REVIEW BEFORE APPLYING:
-- Disable ability for users to UPDATE their role: currently profile self-update RLS does not
-- constrain columns. REVOKE role-column UPDATE grants or replace with a safe RPC first.
revoke update on public.partner_profiles from authenticated;
grant update (display_name) on public.partner_profiles to authenticated;
