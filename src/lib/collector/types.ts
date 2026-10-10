import type { RawCampaign } from "./normalize";

/** A source connector. Add new platforms (incl. overseas) by implementing this and registering in index.ts. */
export interface SourceAdapter {
  id: string;
  name: string;
  collect(): Promise<RawCampaign[]>;
}
