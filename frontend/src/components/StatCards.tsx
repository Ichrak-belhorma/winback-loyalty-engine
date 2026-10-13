import type { Overview } from "../api";
import { humanize, percent } from "../format";

export function StatCards({ overview }: { overview: Overview }) {
  const { customers, messages, reactivation } = overview;
  const blocked = Object.entries(messages.blocked_by_reason)
    .map(([reason, count]) => `${count} ${humanize(reason)}`)
    .join(" · ");
  const aiShare = messages.total ? messages.personalization.ai / messages.total : null;
  const cards = [
    {
      label: "Win-back reactivation",
      value: percent(reactivation.rate),
      hint: `${reactivation.reactivated} of ${reactivation.enrolled} ordered within ${reactivation.window_days} days`,
      tone: "accent",
    },
    {
      label: "Customers",
      value: customers.total.toLocaleString(),
      hint: `${customers.unsubscribed} unsubscribed`,
    },
    {
      label: "Messages sent",
      value: messages.by_status.sent.toLocaleString(),
      hint: `${messages.sent_after_quiet_hours.toLocaleString()} held for quiet hours first`,
    },
    {
      label: "Blocked by compliance",
      value: messages.by_status.blocked.toLocaleString(),
      hint: blocked || "none",
    },
    {
      label: "AI-personalized",
      value: percent(aiShare),
      hint: `${messages.personalization.template.toLocaleString()} used the template`,
    },
  ];
  return (
    <div className="cards">
      {cards.map((card) => (
        <div key={card.label} className={`card ${card.tone ? `card-${card.tone}` : ""}`}>
          <div className="card-label">{card.label}</div>
          <div className="card-value">{card.value}</div>
          <div className="card-hint">{card.hint}</div>
        </div>
      ))}
    </div>
  );
}
