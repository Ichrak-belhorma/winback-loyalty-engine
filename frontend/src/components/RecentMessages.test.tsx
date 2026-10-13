import { render, screen } from "@testing-library/react";
import type { RecentMessage } from "../api";
import { RecentMessages } from "./RecentMessages";

const message: RecentMessage = {
  id: 1,
  created_at: "2026-06-10T16:00:00Z",
  sent_at: null,
  scheduled_for: null,
  customer_id: 9,
  customer_name: "Ana",
  customer_email: "ana@example.com",
  flow: "winback",
  step: "final_offer",
  channel: "sms",
  status: "blocked",
  block_reason: "weekly_cap",
  personalization: "ai",
  subject: "",
  body: "Hi Ana, 20% off your next order.",
};

test("shows status, block reason and copy source for each message", () => {
  render(<RecentMessages messages={[message]} />);

  expect(screen.getByText("blocked")).toHaveClass("badge-blocked");
  expect(screen.getByText(/weekly cap/)).toBeInTheDocument();
  expect(screen.getByText("/ final offer")).toBeInTheDocument();
  expect(screen.getByText("AI")).toBeInTheDocument();
});

test("empty state points to the seed command", () => {
  render(<RecentMessages messages={[]} />);

  expect(screen.getByText(/Run the seed command/)).toBeInTheDocument();
});
