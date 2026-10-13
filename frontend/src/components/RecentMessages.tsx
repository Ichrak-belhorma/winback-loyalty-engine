import type { RecentMessage } from "../api";
import { formatTime, humanize } from "../format";

export function RecentMessages({ messages }: { messages: RecentMessage[] }) {
  if (messages.length === 0) {
    return <p className="empty">No messages yet. Run the seed command to load demo data.</p>;
  }
  return (
    <div className="table-wrap">
      <table className="messages">
        <thead>
          <tr>
            <th>When</th>
            <th>Customer</th>
            <th>Flow / step</th>
            <th>Channel</th>
            <th>Status</th>
            <th>Copy</th>
            <th>Message</th>
          </tr>
        </thead>
        <tbody>
          {messages.map((m) => (
            <tr key={m.id}>
              <td className="nowrap">{formatTime(m.created_at)}</td>
              <td className="nowrap" title={m.customer_email}>
                {m.customer_name}
              </td>
              <td className="nowrap">
                <span className="cap">{m.flow}</span> <span className="muted">/ {humanize(m.step)}</span>
              </td>
              <td className="cap">{m.channel}</td>
              <td className="nowrap">
                <span className={`badge badge-${m.status}`}>{m.status}</span>
                {m.block_reason && <span className="muted small"> {humanize(m.block_reason)}</span>}
              </td>
              <td>{m.personalization === "ai" ? "AI" : "Template"}</td>
              <td className="body" title={m.body}>
                {m.body}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
