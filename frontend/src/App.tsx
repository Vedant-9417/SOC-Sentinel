import { useEffect, useMemo, useState } from "react";
import {
  Shield,
  Activity,
  Bell,
  AlertTriangle,
  Server,
  RefreshCw,
  LogOut,
  Search,
  XCircle,
  CheckCircle2,
  FileDown,
} from "lucide-react";
import { api, WS } from "./api";

type Summary = {
  events_24h: number;
  open_alerts: number;
  critical_alerts: number;
  active_incidents: number;
  severity: Record<string, number>;
};

type Event = {
  id: number;
  source: string;
  event_type: string;
  severity: string;
  source_ip?: string;
  destination_ip?: string;
  username?: string;
  hostname?: string;
  message: string;
  timestamp: string;
};

type Alert = {
  id: number;
  event_id?: number;
  rule_id: string;
  title: string;
  severity: string;
  status: string;
  description: string;
  created_at: string;
};

const sevClass = (s: string) => `sev ${s}`;

function Login({ onLogin }: { onLogin: () => void }) {
  const [username, setUsername] = useState("admin");
  const [password, setPassword] = useState("Admin@12345");
  const [error, setError] = useState("");

  async function submit(e: React.FormEvent) {
    e.preventDefault();

    try {
      const data = await api.login(username, password);
      localStorage.setItem("soc_token", data.access_token);
      onLogin();
    } catch {
      setError("Login failed. Check username/password.");
    }
  }

  return (
    <div className="login-page">
      <div className="login-card">
        <div className="brand">
          <Shield size={34} />
          <div>
            <h1>SOC Sentinel</h1>
            <span>Security Operations Center</span>
          </div>
        </div>

        <form onSubmit={submit}>
          <label>
            Username
            <input
              value={username}
              onChange={(e) => setUsername(e.target.value)}
            />
          </label>

          <label>
            Password
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </label>

          {error && <div className="error">{error}</div>}

          <button className="primary" type="submit">
            Sign in
          </button>
        </form>

        <small>Demo: admin / Admin@12345</small>
      </div>
    </div>
  );
}

function App() {
  const [logged, setLogged] = useState(
    !!localStorage.getItem("soc_token")
  );

  return logged ? (
    <Dashboard
      onLogout={() => {
        localStorage.removeItem("soc_token");
        setLogged(false);
      }}
    />
  ) : (
    <Login onLogin={() => setLogged(true)} />
  );
}

function Dashboard({ onLogout }: { onLogout: () => void }) {
  const [summary, setSummary] = useState<Summary | null>(null);
  const [events, setEvents] = useState<Event[]>([]);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [tab, setTab] = useState<
    "overview" | "events" | "alerts" | "incidents" | "rules"
  >("overview");
  const [search, setSearch] = useState("");
  const [live, setLive] = useState(false);
  const [toast, setToast] = useState("");

  async function load() {
    try {
      const [s, e, a] = await Promise.all([
        api.summary(),
        api.events(),
        api.alerts(),
      ]);

      setSummary(s);
      setEvents(e);
      setAlerts(a);
    } catch (err: unknown) {
      setToast(err instanceof Error ? err.message : "API error");
    }
  }

  useEffect(() => {
    void load();
  }, []);

  useEffect(() => {
    const ws = new WebSocket(`${WS}/ws/live`);

    ws.onopen = () => setLive(true);
    ws.onclose = () => setLive(false);
    ws.onmessage = () => {
      void load();
    };

    const ping = window.setInterval(() => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.send("ping");
      }
    }, 10000);

    return () => {
      window.clearInterval(ping);
      ws.close();
    };
  }, []);

  const filtered = useMemo(
    () =>
      events.filter((e) =>
        `${e.source} ${e.event_type} ${e.source_ip || ""} ${e.message}`
          .toLowerCase()
          .includes(search.toLowerCase())
      ),
    [events, search]
  );

  async function ack(id: number) {
    try {
      await api.acknowledge(id);
      await load();
    } catch (err: unknown) {
      setToast(err instanceof Error ? err.message : "Unable to acknowledge alert");
    }
  }

  async function closeAlert(id: number) {
    try {
      await api.closeAlert(id);
      await load();
    } catch (err: unknown) {
      setToast(err instanceof Error ? err.message : "Unable to close alert");
    }
  }

  return (
    <div className="app">
      <aside>
        <div className="brand side">
          <Shield />
          <div>
            <b>SOC Sentinel</b>
            <span>Blue Team Platform</span>
          </div>
        </div>

        <nav>
          <button
            className={tab === "overview" ? "active" : ""}
            onClick={() => setTab("overview")}
          >
            <Activity />
            Overview
          </button>

          <button
            className={tab === "events" ? "active" : ""}
            onClick={() => setTab("events")}
          >
            <Server />
            Events
          </button>

          <button
            className={tab === "alerts" ? "active" : ""}
            onClick={() => setTab("alerts")}
          >
            <Bell />
            Alerts
          </button>

          <button
            className={tab === "incidents" ? "active" : ""}
            onClick={() => setTab("incidents")}
          >
            <AlertTriangle />
            Incidents
          </button>

          <button
            className={tab === "rules" ? "active" : ""}
            onClick={() => setTab("rules")}
          >
            <Shield />
            Detection Rules
          </button>
        </nav>

        <div className="side-bottom">
          <div className="live">
            <span className={live ? "dot on" : "dot"} />
            {live ? "Live" : "Disconnected"}
          </div>

          <button onClick={() => void load()}>
            <RefreshCw />
            Refresh
          </button>

          <button onClick={onLogout}>
            <LogOut />
            Logout
          </button>
        </div>
      </aside>

      <main>
        <header>
          <div>
            <h2>
              {tab === "overview"
                ? "SOC Overview"
                : tab[0].toUpperCase() + tab.slice(1)}
            </h2>
            <p>Real-time defensive monitoring and incident response</p>
          </div>

          <div className="header-right">
            <span className="pill">API Connected</span>
            <span className="clock">{new Date().toLocaleString()}</span>
          </div>
        </header>

        {toast && (
          <div className="toast" onClick={() => setToast("")}>
            {toast}
            <XCircle />
          </div>
        )}

        {tab === "overview" && summary && (
          <Overview
            summary={summary}
            alerts={alerts}
            onAck={ack}
            onClose={closeAlert}
          />
        )}

        {tab === "events" && (
          <Events
            events={filtered}
            search={search}
            setSearch={setSearch}
          />
        )}

        {tab === "alerts" && (
          <Alerts alerts={alerts} onAck={ack} onClose={closeAlert} />
        )}

        {tab === "incidents" && <Incidents onCreated={load} />}

        {tab === "rules" && <Rules />}
      </main>
    </div>
  );
}

function Metric({
  icon,
  title,
  value,
  danger,
}: {
  icon: React.ReactNode;
  title: string;
  value: number;
  danger?: boolean;
}) {
  return (
    <div className={danger ? "metric danger" : "metric"}>
      <div className="metric-icon">{icon}</div>
      <div>
        <span>{title}</span>
        <strong>{value}</strong>
      </div>
    </div>
  );
}

function Overview({
  summary,
  alerts,
  onAck,
  onClose,
}: {
  summary: Summary;
  alerts: Alert[];
  onAck: (id: number) => void;
  onClose: (id: number) => void;
}) {
  const severityOrder = ["critical", "high", "medium", "low"];

  const maxSeverity = Math.max(
    1,
    ...severityOrder.map((severity) => summary.severity[severity] || 0)
  );

  const openCount = alerts.filter(
    (alert) => alert.status === "open"
  ).length;

  const acknowledgedCount = alerts.filter(
    (alert) => alert.status === "acknowledged"
  ).length;

  const closedCount = alerts.filter(
    (alert) => alert.status === "closed"
  ).length;

  const recentAlerts = [...alerts]
    .sort(
      (a, b) =>
        new Date(b.created_at).getTime() -
        new Date(a.created_at).getTime()
    )
    .slice(0, 6);

  return (
    <div className="content advanced-overview">
      <section className="overview-welcome">
        <div>
          <span className="eyebrow">SECURITY OPERATIONS CENTER</span>
          <h3>Advanced Security Overview</h3>
          <p>
            Monitor security events, alert workload and incident response
            from one dashboard.
          </p>
        </div>

        <div className="overview-live">
          <span className="dot on" />
          SOC Monitoring
        </div>
      </section>

      <section className="cards">
        <Metric
          icon={<Activity />}
          title="Events / 24h"
          value={summary.events_24h}
        />

        <Metric
          icon={<Bell />}
          title="Open Alerts"
          value={summary.open_alerts}
        />

        <Metric
          icon={<AlertTriangle />}
          title="Critical Alerts"
          value={summary.critical_alerts}
          danger
        />

        <Metric
          icon={<Server />}
          title="Active Incidents"
          value={summary.active_incidents}
        />
      </section>

      <section className="grid-two advanced-grid">
        <div className="panel">
          <div className="panel-head">
            <div>
              <h3>Security Event Severity</h3>
              <span>Severity distribution from the API</span>
            </div>
            <span className="analytics-tag">EVENTS</span>
          </div>

          <div className="severity-list advanced-severity-list">
            {severityOrder.map((severity) => {
              const count = summary.severity[severity] || 0;
              const width =
                count === 0 ? 0 : Math.max(5, (count / maxSeverity) * 100);

              return (
                <div
                  className={`bar-row severity-${severity}`}
                  key={severity}
                >
                  <span>{severity}</span>

                  <div className="bar">
                    <i style={{ width: `${width}%` }} />
                  </div>

                  <b>{count}</b>
                </div>
              );
            })}
          </div>

          <div className="analytics-footnote">
            Higher severity events should be investigated first.
          </div>
        </div>

        <div className="panel">
          <div className="panel-head">
            <div>
              <h3>Alert Workflow</h3>
              <span>Current alert status summary</span>
            </div>
          </div>

          <div className="alert-workflow-stats">
            <div className="workflow-stat workflow-open">
              <span>Open</span>
              <strong>{openCount}</strong>
            </div>

            <div className="workflow-stat workflow-ack">
              <span>Acknowledged</span>
              <strong>{acknowledgedCount}</strong>
            </div>

            <div className="workflow-stat workflow-closed">
              <span>Closed</span>
              <strong>{closedCount}</strong>
            </div>
          </div>

          <div className="workflow-note">
            <Shield size={18} />
            <span>
              Review open alerts, acknowledge alerts under investigation,
              and close alerts after handling.
            </span>
          </div>
        </div>
      </section>

      <section className="panel recent-alerts-panel">
        <div className="panel-head">
          <div>
            <h3>Recent Security Alerts</h3>
            <span>Latest alerts received from SOC Sentinel</span>
          </div>

          <span className="analytics-tag">
            LATEST {recentAlerts.length}
          </span>
        </div>

        <div className="compact-list">
          {recentAlerts.length > 0 ? (
            recentAlerts.map((alert) => (
              <AlertRow
                key={alert.id}
                alert={alert}
                onAck={onAck}
                onClose={onClose}
              />
            ))
          ) : (
            <div className="dashboard-empty">
              <CheckCircle2 size={22} />
              <div>
                <b>No alerts available</b>
                <span>
                  New alerts will appear here when the backend returns them.
                </span>
              </div>
            </div>
          )}
        </div>
      </section>
    </div>
  );
}

function AlertRow({
  alert,
  onAck,
  onClose,
}: {
  alert: Alert;
  onAck: (id: number) => void;
  onClose: (id: number) => void;
}) {
  return (
    <div className="alert-row">
      <div>
        <span className={sevClass(alert.severity)}>{alert.severity}</span>
        <b>{alert.title}</b>
        <small>{alert.description}</small>
      </div>

      <div className="actions">
        {alert.status === "open" && (
          <button onClick={() => onAck(alert.id)} title="Acknowledge">
            <CheckCircle2 />
          </button>
        )}

        {alert.status !== "closed" && (
          <button onClick={() => onClose(alert.id)} title="Close">
            <XCircle />
          </button>
        )}
      </div>
    </div>
  );
}

function Events({
  events,
  search,
  setSearch,
}: {
  events: Event[];
  search: string;
  setSearch: (s: string) => void;
}) {
  const [downloading, setDownloading] = useState<number | null>(null);
  const [error, setError] = useState("");

  async function downloadReport(id: number) {
    try {
      setDownloading(id);
      setError("");
      await api.eventReport(id);
    } catch (err: unknown) {
      setError(
        err instanceof Error ? err.message : "PDF report download failed."
      );
    } finally {
      setDownloading(null);
    }
  }

  return (
    <div className="content">
      <div className="panel">
        <div className="toolbar">
          <div className="search">
            <Search />
            <input
              placeholder="Search events..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
          <span>{events.length} events</span>
        </div>

        {error && <div className="error">{error}</div>}

        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Time</th>
                <th>Severity</th>
                <th>Source</th>
                <th>Type</th>
                <th>Source IP</th>
                <th>Host</th>
                <th>Message</th>
                <th>PDF Report</th>
              </tr>
            </thead>

            <tbody>
              {events.map((e) => (
                <tr key={e.id}>
                  <td>{new Date(e.timestamp).toLocaleTimeString()}</td>
                  <td>
                    <span className={sevClass(e.severity)}>
                      {e.severity}
                    </span>
                  </td>
                  <td>{e.source}</td>
                  <td>{e.event_type}</td>
                  <td>{e.source_ip || "—"}</td>
                  <td>{e.hostname || "—"}</td>
                  <td>{e.message}</td>
                  <td>
                    <button
                      type="button"
                      onClick={() => void downloadReport(e.id)}
                      disabled={downloading !== null}
                      title={`Download PDF report for event ${e.id}`}
                    >
                      <FileDown size={16} />
                      {downloading === e.id
                        ? "Generating..."
                        : "Download PDF"}
                    </button>
                  </td>
                </tr>
              ))}

              {events.length === 0 && (
                <tr>
                  <td colSpan={8}>No events found.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

function Alerts({
  alerts,
  onAck,
  onClose,
}: {
  alerts: Alert[];
  onAck: (id: number) => void;
  onClose: (id: number) => void;
}) {
  return (
    <div className="content">
      <div className="panel">
        <div className="panel-head">
          <h3>Alert Queue</h3>
          <span>{alerts.filter((a) => a.status === "open").length} open</span>
        </div>

        <div className="alert-list">
          {alerts.map((a) => (
            <AlertRow
              key={a.id}
              alert={a}
              onAck={onAck}
              onClose={onClose}
            />
          ))}
        </div>
      </div>
    </div>
  );
}

function Incidents({ onCreated }: { onCreated: () => void }) {
  const [items, setItems] = useState<any[]>([]);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [severity, setSeverity] = useState("medium");
  const [error, setError] = useState("");

  async function load() {
    try {
      setItems(await api.incidents());
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Unable to load incidents");
    }
  }

  useEffect(() => {
    void load();
  }, []);

  async function create() {
    if (!title.trim() || !description.trim()) {
      setError("Please enter both title and description.");
      return;
    }

    try {
      setError("");
      await api.createIncident({ title, description, severity });
      setTitle("");
      setDescription("");
      await load();
      onCreated();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Unable to create incident");
    }
  }

  return (
    <div className="content grid-two">
      <div className="panel">
        <div className="panel-head">
          <h3>Create Incident</h3>
        </div>

        {error && <div className="error">{error}</div>}

        <label>
          Title
          <input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Suspicious workstation activity"
          />
        </label>

        <label>
          Severity
          <select
            value={severity}
            onChange={(e) => setSeverity(e.target.value)}
          >
            <option value="low">low</option>
            <option value="medium">medium</option>
            <option value="high">high</option>
            <option value="critical">critical</option>
          </select>
        </label>

        <label>
          Description
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows={5}
          />
        </label>

        <button className="primary" onClick={() => void create()}>
          Create Incident
        </button>
      </div>

      <div className="panel">
        <div className="panel-head">
          <h3>Incident Queue</h3>
        </div>

        {items.map((i) => (
          <div className="incident" key={i.id}>
            <div>
              <span className={sevClass(i.severity)}>{i.severity}</span>
              <b>{i.title}</b>
              <p>{i.description}</p>
            </div>
            <span className="status">{i.status}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function Rules() {
  const [rules, setRules] = useState<any[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    api.rules()
      .then(setRules)
      .catch((err: unknown) => {
        setError(err instanceof Error ? err.message : "Unable to load rules");
      });
  }, []);

  return (
    <div className="content">
      <div className="panel">
        <div className="panel-head">
          <h3>Detection Engineering</h3>
          <span>{rules.length} loaded rules</span>
        </div>

        {error && <div className="error">{error}</div>}

        {rules.map((r) => (
          <div className="rule" key={r.rule_id}>
            <div>
              <code>{r.rule_id}</code>
              <b>{r.name}</b>
              <p>{r.description}</p>
            </div>
            <span className={r.enabled ? "enabled" : "disabled"}>
              {r.enabled ? "ENABLED" : "DISABLED"}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

export default App;

