export type EventStatus =
  | "announced"
  | "upcoming"
  | "airing"
  | "released"
  | "downloaded"
  | "missing";

export type EventType =
  | "ppv"
  | "fight_night"
  | "on_abc"
  | "tuf_finale"
  | "other";

export interface Event {
  id: number;
  slug: string;
  title: string;
  event_number: number | null;
  event_type: EventType;
  event_date: string; // ISO date
  venue: string | null;
  location: string | null;
  main_event: string | null;
  co_main_event: string | null;
  status: EventStatus;
  monitored: boolean;
  quality: string | null;
}

export interface QueueItem {
  id: number;
  event_id: number;
  release_title: string;
  status: "grabbed" | "downloading" | "completed" | "failed" | "imported";
  progress_percent: number;
}

export interface Indexer {
  id: number;
  name: string;
  url: string;
  api_key: string;
  enabled: boolean;
  priority: number;
  categories: string;
}
