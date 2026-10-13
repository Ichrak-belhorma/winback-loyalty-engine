import { useCallback, useEffect, useState } from "react";
import {
  fetchDaily,
  fetchOverview,
  fetchRecent,
  type DailyPoint,
  type Overview,
  type RecentMessage,
} from "./api";
import { FlowTable } from "./components/FlowTable";
import { MessagesChart } from "./components/MessagesChart";
import { RecentMessages } from "./components/RecentMessages";
import { SegmentChart } from "./components/SegmentChart";
import { StatCards } from "./components/StatCards";

const REFRESH_MS = 30_000;
const DAYS = 45;

export function App() {
  const [overview, setOverview] = useState<Overview | null>(null);
  const [daily, setDaily] = useState<DailyPoint[]>([]);
  const [recent, setRecent] = useState<RecentMessage[]>([]);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const [o, d, r] = await Promise.all([fetchOverview(), fetchDaily(DAYS), fetchRecent(25)]);
      setOverview(o);
      setDaily(d);
      setRecent(r);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }, []);

  useEffect(() => {
    void load();
    const timer = setInterval(() => void load(), REFRESH_MS);
    return () => clearInterval(timer);
  }, [load]);

  return (
    <div className="app">
      <header className="topbar">
        <h1>Retention Dashboard</h1>
        <span className="muted">Win-back and loyalty engine · refreshes every 30s</span>
      </header>
      {error && <div className="error-banner">Could not load data: {error}</div>}
      {!overview ? (
        <p className="empty">Loading…</p>
      ) : (
        <>
          <StatCards overview={overview} />
          <div className="grid">
            <section className="panel">
              <h2>Customers by segment</h2>
              <SegmentChart segments={overview.segments} />
            </section>
            <section className="panel">
              <h2>Messages sent per day (last {DAYS} days)</h2>
              <MessagesChart data={daily} />
            </section>
          </div>
          <section className="panel">
            <h2>Flows</h2>
            <FlowTable overview={overview} />
          </section>
          <section className="panel">
            <h2>Recent messages</h2>
            <RecentMessages messages={recent} />
          </section>
        </>
      )}
    </div>
  );
}
