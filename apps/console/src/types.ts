export interface ReviewQueueItem {
  upload_id: string;
  tenant_id: string;
  filename: string;
  created_at: string;
  yellow_frame_count: number;
  total_frames: number;
  status: string;
}

export interface ReviewQueueResponse {
  items: ReviewQueueItem[];
  total_count: number;
  offset: number;
  limit: number;
}

export interface FrameForensicPackage {
  frame_index: number;
  timestamp_seconds: number;
  color: "RED" | "YELLOW" | "GREEN";
  manipulation_score: number;
  sensitivity_score: number;
  uncertainty: number;
  cues: Record<string, number>;
  thumbnail_blurred_b64?: string | null;
  sha256_hash: string;
}

export interface ReviewPackageResponse {
  upload_id: string;
  tenant_id: string;
  filename: string;
  mime_type: string;
  file_size_bytes: number;
  sha256_hash: string;
  quarantine_key: string;
  verdict: string;
  created_at: string;
  frames: FrameForensicPackage[];
  wellness_warning: string;
}

export interface ReviewerActionRequest {
  action: "APPROVE" | "REJECT";
  reviewer_id: string;
  notes: string;
  category?: string;
}

export interface ReviewerActionResponse {
  upload_id: string;
  verdict: "ALLOW" | "BLOCK";
  reviewed_by: string;
  action_recorded_at: string;
  audit_entry_id: number;
}
