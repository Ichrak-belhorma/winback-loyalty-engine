export type Flow = "welcome" | "winback" | "review" | "referral";
export const FLOWS: Flow[] = ["welcome", "winback", "review", "referral"];

export interface SegmentCount {
  segment: string;
  label: string;
  count: number;
}

export interface FlowMessageCounts {
  flow: Flow;
  sent: number;
  blocked: number;
  deferred: number;
  failed: number;
}

export interface Overview {
  customers: { total: number; unsubscribed: number };
  segments: SegmentCount[];
  inactivity: Record<"active" | "inactive_30" | "inactive_60" | "inactive_90", number>;
  messages: {
    total: number;
    by_status: Record<"pending" | "sent" | "deferred" | "blocked" | "failed", number>;
    by_flow: FlowMessageCounts[];
    blocked_by_reason: Record<string, number>;
    sent_after_quiet_hours: number;
    personalization: Record<"ai" | "template", number>;
  };
  reactivation: {
    window_days: number;
    enrolled: number;
    reactivated: number;
    rate: number | null;
    in_progress: number;
  };
  active_enrollments: Record<Flow, number>;
}

export type DailyPoint = { date: string; total: number } & Record<Flow, number>;

export interface RecentMessage {
  id: number;
  created_at: string;
  sent_at: string | null;
  scheduled_for: string | null;
  customer_id: number;
  customer_name: string;
  customer_email: string;
  flow: Flow;
  step: string;
  channel: "email" | "sms";
  status: "pending" | "sent" | "deferred" | "blocked" | "failed";
  block_reason: string;
  personalization: "ai" | "template";
  subject: string;
  body: string;
}

async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(path, { headers: { Accept: "application/json" } });
  if (!response.ok) throw new Error(`${response.status} ${response.statusText} for ${path}`);
  return (await response.json()) as T;
}

export const fetchOverview = () => getJson<Overview>("/api/stats/overview");
export const fetchDaily = (days: number) =>
  getJson<DailyPoint[]>(`/api/stats/messages-over-time?days=${days}`);
export const fetchRecent = (limit: number) =>
  getJson<RecentMessage[]>(`/api/messages/recent?limit=${limit}`);
