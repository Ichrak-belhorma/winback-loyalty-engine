import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { FLOWS, type DailyPoint } from "../api";
import { FLOW_COLORS } from "../colors";
import { shortDate } from "../format";

export function MessagesChart({ data }: { data: DailyPoint[] }) {
  return (
    <ResponsiveContainer width="100%" height={260}>
      <LineChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: -12 }}>
        <CartesianGrid strokeDasharray="3 3" vertical={false} />
        <XAxis dataKey="date" tickFormatter={shortDate} minTickGap={24} tickLine={false} />
        <YAxis allowDecimals={false} tickLine={false} />
        <Tooltip labelFormatter={(value) => shortDate(String(value))} />
        <Legend />
        {FLOWS.map((flow) => (
          <Line
            key={flow}
            type="monotone"
            dataKey={flow}
            stroke={FLOW_COLORS[flow]}
            strokeWidth={2}
            dot={false}
          />
        ))}
      </LineChart>
    </ResponsiveContainer>
  );
}
