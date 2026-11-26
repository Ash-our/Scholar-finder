export type Degree =
  "bachelor" | "master" | "phd" | "postdoc" | "research" | "other";
export type Status = "open" | "upcoming" | "closed" | "unverified";
export interface Placement {
  id: string;
  name: string;
  country: string;
  lat: number;
  lon: number;
  precision: "campus" | "city" | "country";
  source_url: string;
}
export interface MatchResult {
  compatible: boolean;
  status: "matched" | "potential" | "excluded";
  score: number;
  reasons: string[];
  uncertainties: string[];
  excluded_reasons: string[];
}
export interface Scholarship {
  id: string;
  source_id: string;
  source_record_id: string;
  title: string;
  title_ar: string | null;
  provider: string;
  source_url: string;
  official_url: string | null;
  cycle: string | null;
  countries: string[];
  degrees: Degree[];
  fields: string[];
  funding: string;
  description: string;
  eligibility_text: string;
  nationalities: string[];
  excluded_nationalities: string[];
  minimum_gpa: number | null;
  gpa_scale: number | null;
  extra_requirements: string[];
  deadline: string | null;
  deadline_text: string;
  deadline_confidence: "confirmed" | "estimated" | "recurring" | "unknown";
  opens_at: string | null;
  open_evidence: "accepting_applications" | "date_window" | "rolling" | null;
  reported_status: string;
  application_state: Status;
  official_verified_at: string | null;
  verification_note: string;
  fetched_at: string;
  source_checked_at: string | null;
  placements: Placement[];
  identity_resolved: boolean;
  added_at: string | null;
  updated_at: string | null;
  first_streamed_at: string | null;
  last_event_id: string | null;
  last_observed_at: string | null;
  ingestion_mode: "live" | "import" | "replay" | "test" | null;
  match?: MatchResult;
}
export interface Profile {
  nationality: string;
  gpa: number | null;
  gpa_scale: number;
  field: string;
  degree: Degree;
  preferred_countries: string[];
}
export interface Filters {
  q: string;
  country: string;
  degree: string;
  field: string;
  funding: string;
  status: Status | "all" | "discover";
  sort: "deadline" | "newest" | "added" | "title";
  placement: string;
  bbox: string;
}
export interface MapGroup extends Placement {
  cluster_countries?: string[];
  cluster_bounds?: [[number, number], [number, number]];
  key: string;
  scholarship_ids: string[];
  confirmed_scholarship_ids: string[];
  confirmed_count: number;
  unverified_count: number;
}
export interface MapData {
  countries: CountrySummary[];
  groups: MapGroup[];
  opportunity_count: number;
  unverified_listing_count: number;
  placement_count: number;
  unmapped_count: number;
}
export interface CountrySummary {
  country: string;
  listing_count: number;
  confirmed_count: number;
  university_count: number;
  unlocated_count: number;
}
export interface CollectionSchedule {
  scheduler_connected?: boolean;
  status: "running" | "waiting" | "finished";
  interval_seconds: number;
  run_started_at: string;
  last_finished_at?: string;
  last_heartbeat_at?: string;
  next_run_at: string | null;
  last_run_succeeded?: boolean;
}
export interface StreamEvent {
  event_id: string;
  scholarship_id: string;
  title: string;
  source_id: string;
  event_type: "discovered" | "updated" | "closed";
  observed_at: string;
  processed_at: string;
  mode: "live" | "replay";
  applied: boolean;
  transport: { topic: string; partition: number; offset: number } | null;
}
export interface ActivityResponse {
  events: StreamEvent[];
  streaming: {
    processed_events: number;
    invalid_events: number;
    processor_connected: boolean;
    runtime?: { last_heartbeat_at?: string; active_queries?: string[] };
  } | null;
  schedule: CollectionSchedule | null;
  generated_at: string;
}
export interface CatalogueResponse {
  items: Scholarship[];
  total: number;
  offset: number;
  limit: number;
  confirmed_count: number;
  unverified_listing_count: number;
  map: MapData;
  status_counts: Partial<Record<Status, number>>;
  generated_at: string;
  last_fetched_at: string | null;
}
export interface Metadata {
  countries: { code: string; name: string }[];
  fields: string[];
  degrees: Degree[];
  mode?: "live" | "replay";
}
export interface SourceRun {
  status: "ok" | "partial" | "error" | "running";
  last_success_at?: string;
  last_started_at?: string;
  records?: number;
  published?: number;
  unchanged?: number;
  error?: string;
  sink?: string;
}
export interface SourceInfo {
  id: string;
  name: string;
  url: string;
  adapter: boolean;
  note?: string;
  last_run: SourceRun | null;
}
export interface StreamWindow {
  source_id: string;
  event_type: string;
  window_start: string;
  window_end: string;
  count: number;
  updated_at: string;
}
export interface SourceResponse {
  schedule?: CollectionSchedule | null;
  sources: SourceInfo[];
  streaming: {
    windows: StreamWindow[];
    processed_events: number;
    invalid_events: number;
  } | null;
}
export interface InsightsData {
  computed_at: string;
  engine: string;
  total_listings: number;
  confirmed_opportunities: number;
  by_country: { country: string; opportunities: number }[];
  by_degree: { degree: string; opportunities: number }[];
  by_funding: { funding: string; opportunities: number }[];
  by_status: { status: string; listings: number }[];
  upcoming_deadlines: { id: string; title: string; deadline: string }[];
  near_duplicate_pairs?: number;
}
