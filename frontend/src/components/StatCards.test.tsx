import { render, screen } from "@testing-library/react";
import type { Overview } from "../api";
import { StatCards } from "./StatCards";

const overview: Overview = {
  customers: { total: 2000, unsubscribed: 12 },
  segments: [{ segment: "champions", label: "Champions", count: 400 }],
  inactivity: { active: 900, inactive_30: 300, inactive_60: 200, inactive_90: 600 },
  messages: {
    total: 1000,
    by_status: { pending: 0, sent: 930, deferred: 10, blocked: 60, failed: 0 },
    by_flow: [{ flow: "winback", sent: 600, blocked: 40, deferred: 5, failed: 0 }],
    blocked_by_reason: { weekly_cap: 45, unsubscribed: 15 },
    sent_after_quiet_hours: 120,
    personalization: { ai: 250, template: 750 },
  },
  reactivation: { window_days: 14, enrolled: 400, reactivated: 72, rate: 0.18, in_progress: 30 },
  active_enrollments: { welcome: 3, winback: 30, review: 8, referral: 0 },
};

test("shows reactivation rate, compliance blocks and AI share", () => {
  render(<StatCards overview={overview} />);

  expect(screen.getByText("18.0%")).toBeInTheDocument();
  expect(screen.getByText("72 of 400 ordered within 14 days")).toBeInTheDocument();
  expect(screen.getByText("45 weekly cap · 15 unsubscribed")).toBeInTheDocument();
  expect(screen.getByText("25.0%")).toBeInTheDocument();
});

test("reactivation shows a dash before anyone has enrolled", () => {
  render(
    <StatCards
      overview={{
        ...overview,
        reactivation: { window_days: 14, enrolled: 0, reactivated: 0, rate: null, in_progress: 0 },
      }}
    />,
  );

  expect(screen.getByText("Win-back reactivation").nextSibling).toHaveTextContent("—");
});
