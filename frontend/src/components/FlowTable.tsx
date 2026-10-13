import type { Overview } from "../api";

export function FlowTable({ overview }: { overview: Overview }) {
  return (
    <table className="mini">
      <thead>
        <tr>
          <th>Flow</th>
          <th className="num">Sent</th>
          <th className="num">Blocked</th>
          <th className="num">Waiting</th>
          <th className="num">Active enrollments</th>
        </tr>
      </thead>
      <tbody>
        {overview.messages.by_flow.map((row) => (
          <tr key={row.flow}>
            <td className="cap">{row.flow}</td>
            <td className="num">{row.sent.toLocaleString()}</td>
            <td className="num">{row.blocked.toLocaleString()}</td>
            <td className="num">{row.deferred.toLocaleString()}</td>
            <td className="num">{overview.active_enrollments[row.flow].toLocaleString()}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
