// Tipos compartidos del frontend de Photonix AI

export type Role = "admin" | "client";

export interface PlanFeatures {
  max_batch_photos: number | null; // null = ilimitado
  object_removal: boolean;
  watermark_multi: boolean;
  priority_processing: boolean;
}

export interface Profile {
  id: string;
  email: string;
  full_name: string | null;
  role: Role;
  accepted_terms: boolean;
  trial_ends_at: string | null;
  membership_plan: string | null;
  membership_status: string | null;
  active_plan: string | null;
  plan_features: PlanFeatures | null;
}

export interface ReminderDue {
  user_id: string;
  email: string;
  full_name: string | null;
  plan: string;
  ends_at: string;
  expired: boolean;
  is_blocked: boolean;
}

export interface AdminUser {
  user_id: string;
  email: string;
  full_name: string | null;
  plan: string;
  ends_at: string | null;
  active: boolean;
  is_blocked: boolean;
  created_at: string;
}

export interface PlanInfo {
  id: string;
  name: string;
  price_crc: number;
  duration_days: number | null;
}

export interface SinpePaymentHistoryItem {
  id: string;
  plan: string;
  status: "pending" | "approved" | "rejected";
  created_at: string;
  reviewed_at: string | null;
}

export interface SupportTicket {
  id: string;
  user_id: string;
  subject: string;
  message: string;
  status: "open" | "in_progress" | "closed";
  admin_reply: string | null;
  created_at: string;
  updated_at: string;
}

export interface SupportTicketAdminView extends SupportTicket {
  profiles?: { email: string } | null;
}

export interface FeedbackAdminView {
  id: string;
  user_id: string;
  project_id: string | null;
  rating: number;
  comment: string | null;
  status: "pending" | "in_review" | "implemented" | "discarded";
  created_at: string;
  profiles?: { email: string } | null;
  projects?: { total_count: number } | null;
}

export interface SinpePaymentAdminView {
  id: string;
  user_id: string;
  user_email: string | null;
  plan: string;
  receipt_image_url: string;
  status: string;
  created_at: string;
}

export interface NewUsersStatsPoint {
  date: string;
  new_users: number;
}

export type WatermarkPosition = "north" | "south" | "east" | "west" | "center" | "custom";

export interface StyleProfile {
  id: string;
  label: string;
  emoji: string;
  description: string;
  estimated_seconds_per_photo: number;
  improvement_level: "adaptativo" | "sutil" | "moderado" | "alto";
  params: Record<string, number> | null;
  suggest_remove_plates: boolean;
  suggest_remove_poles_wires: boolean;
}

export interface PreviewPair {
  photo_id: string;
  original_url: string;
  edited_url: string;
}

export interface ProjectSummary {
  id: string;
  name: string;
  status: string; // 'processing' | 'review'
  processed_count: number;
  total_count: number;
  created_at: string;
  photo_count: number;
}

export interface UploadStatsSummary {
  photos_this_month: number;
  recent_projects: {
    id: string;
    name: string;
    status: string;
    processed_count: number;
    total_count: number;
    created_at: string;
  }[];
}
