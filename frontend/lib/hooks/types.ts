// API Response Types (matching backend schemas)

export interface PlanSummaryOut {
  plan_id: string;
  status: string;
  section_id: string;
  section_name: string;
  division_name: string | null;
  zone_name: string | null;
  block_count: number;
  request_count: number;
  total_block_duration_minutes: number;
  created_at: string; // ISO datetime
  synced_at: string; // ISO datetime
}

export interface BlockOut {
  block_id: string;
  plan_id: string;
  plan_status: string;
  track_id: string;
  track_code: string;
  track_name: string;
  section_name: string | null;
  start_time: string; // ISO datetime
  end_time: string; // ISO datetime
  is_merged: boolean;
  request_count: number;
  synced_at: string; // ISO datetime
}

export interface TrackOut {
  track_id: string;
  code: string;
  name: string;
  line: string | null;
  direction: string | null;
  is_active: boolean;
  section_id: string;
  section_name: string;
  division_name: string | null;
  zone_name: string | null;
  synced_at: string; // ISO datetime
}

export interface TrainOut {
  train_id: string;
  train_number: string;
  train_type: string | null;
  is_active: boolean;
  schedule_count: number;
  synced_at: string; // ISO datetime
}

export interface BlockRequestResponse {
  id: string;
  department_id: string;
  requested_by_user_id: string;
  request_type: "technical" | "operational";
  priority: "normal" | "high" | "emergency";
  track_id: string;
  requested_start: string; // ISO datetime
  requested_end: string; // ISO datetime
  status: string;
  is_emergency: boolean;
  submitted_at: string | null; // ISO datetime
  created_at: string; // ISO datetime
}

export interface TechnicalRequestPayload {
  train_stops?: string | null;
  railway_line?: string | null;
  direction?: string | null;
  restriction_type?: string | null;
  train_type?: string | null;
  finance_reference?: string | null;
  responsible_department_id?: string | null;
  additional_parameters?: Record<string, unknown> | null;
}

export interface OperationalRequestPayload {
  reason: string; // e.g., BRIDGE, UNDERPASS, ROAD_CROSSING, TREE_WORK
  reason_details?: string | null;
  expected_duration_minutes?: number | null;
  safety_notes?: string | null;
  additional_parameters?: Record<string, unknown> | null;
}

export interface BlockRequestCreate {
  department_id: string;
  requested_by_user_id: string;
  request_type: "technical" | "operational";
  priority?: "normal" | "high" | "emergency";
  track_id: string;
  requested_start: string; // ISO datetime
  requested_end: string; // ISO datetime
  is_emergency?: boolean;
  affected_track_ids?: string[];
  technical?: TechnicalRequestPayload | null;
  operational?: OperationalRequestPayload | null;
}

export interface BlockRequestUpdate {
  requested_start?: string | null;
  requested_end?: string | null;
  priority?: string | null;
  is_emergency?: boolean | null;
  affected_track_ids?: string[] | null;
  technical?: TechnicalRequestPayload | null;
  operational?: OperationalRequestPayload | null;
}
