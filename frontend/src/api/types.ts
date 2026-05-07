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
  poster_url: string | null;
  tmdb_id: number | null;
  source_url: string | null;
}

export interface QueueItem {
  id: number;
  event_id: number;
  release_title: string;
  release_size_bytes: number | null;
  indexer_name: string | null;
  download_client_id: number | null;
  status: "grabbed" | "downloading" | "completed" | "failed" | "imported";
  progress_percent: number;
  error_message: string | null;
  download_path: string | null;
  grabbed_at: string;
  completed_at: string | null;
}

export type IndexerType = "newznab" | "torznab";

export interface Indexer {
  id: number;
  name: string;
  indexer_type: IndexerType;
  url: string;
  api_key: string;
  enabled: boolean;
  priority: number;
  categories: string;
}

export interface SearchRelease {
  title: string;
  size_bytes: number | null;
  indexer_name: string;
  nzb_url: string;
  pub_date: string | null;
  guid: string | null;
}

export interface HistoryItem {
  id: number;
  release_title: string;
  release_size_bytes: number | null;
  indexer_name: string | null;
  status: "grabbed" | "downloading" | "completed" | "failed" | "imported";
  progress_percent: number;
  grabbed_at: string;
  completed_at: string | null;
  error_message: string | null;
}

export interface AppSettings {
  media_root: string;
  use_hardlinks: boolean;
  tmdb_api_key: string;
  plex_host: string;
  plex_token: string;
  plex_section_id: string;
  jellyfin_host: string;
  jellyfin_token: string;
  jellyfin_library_id: string;
}

export interface ScheduledTask {
  id: string;
  name: string;
  next_run_time: string | null;
}

export type DownloadClientType =
  | "sabnzbd"
  | "nzbget"
  | "qbittorrent"
  | "deluge"
  | "transmission"
  | "real_debrid";

export interface DownloadClient {
  id: number;
  name: string;
  client_type: DownloadClientType;
  host: string;
  api_key: string | null;
  username: string | null;
  password: string | null;
  category: string;
  enabled: boolean;
  priority: number;
}
