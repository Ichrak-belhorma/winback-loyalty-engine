import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { SegmentCount } from "../api";
import { SEGMENT_COLORS } from "../colors";

export function SegmentChart({ segments }: { segments: SegmentCount[] }) {
  return (
    <ResponsiveContainer width="100%" height={260}>
      <BarChart data={segments} margin={{ top: 8, right: 8, bottom: 0, left: -12 }}>
        <CartesianGrid strokeDasharray="3 3" vertical={false} />
        <XAxis dataKey="label" tickLine={false} />
        <YAxis allowDecimals={false} tickLine={false} />
        <Tooltip cursor={{ fill: "rgba(0,0,0,0.04)" }} />
        <Bar dataKey="count" name="Customers" radius={[4, 4, 0, 0]}>
          {segments.map((s) => (
            <Cell key={s.segment} fill={SEGMENT_COLORS[s.segment] ?? "#868e96"} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
