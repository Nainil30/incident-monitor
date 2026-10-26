import { useCallback, useEffect, useState } from "react";
import { api } from "./api.js";

function timeAgo(iso) {
  const mins = Math.round((Date.now() - new Date(iso).getTime()) / 60000);
  if (mins < 60) return `${mins}m ago`;
  if (mins < 1440) return `${Math.floor(mins / 60)}h ${mins % 60}m ago`;
  return `${Math.floor(mins / 1440)}d ago`;
}

const fmtTime = (iso) => new Date(iso).toLocaleTimeString();

function SummaryCards({ stats }) {
  if (!stats) return null;
  const cards = [
    { label: "Open", value: stats.by_status.open, cls: "open" },
    { label: "Acknowledged", value: stats.by_status.acknowledged, cls: "acknowledged" },
    { label: "Resolved", value: stats.by_status.resolved, cls: "resolved" },
    { label: "Active SEV1", value: stats.active_by_severity.SEV1, cls: "sev1" },
  ];
  return (
    <div className="cards">
      {cards.map((c) => (
        <div key={c.label} className={`card card-${c.cls}`}>
          <div className="card-value">{c.value}</div>
          <div className="card-label">{c.label}</div>
        </div>
      ))}
    </div>
  );
}

function IncidentTable({ incidents, selectedId, onSelect, filters, setFilters }) {
  return (
    <section className="panel">
      <div className="panel-header">
        <h2>Incidents</h2>
        <div className="filters">
          <select value={filters.status} onChange={(e) => setFilters({ ...filters, status: e.target.value })}>
            <option value="">All statuses</option>
            <option value="open">Open</option>
            <option value="acknowledged">Acknowledged</option>
            <option value="resolved">Resolved</option>
          </select>
          <select value={filters.severity} onChange={(e) => setFilters({ ...filters, severity: e.target.value })}>
            <option value="">All severities</option>
            {["SEV1", "SEV2", "SEV3", "SEV4"].map((s) => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>
        </div>
      </div>
      <table>
        <thead>
          <tr><th>ID</th><th>Title</th><th>Severity</th><th>Services</th><th>Status</th><th>Age</th></tr>
        </thead>
        <tbody>
          {incidents.map((i) => (
            <tr key={i.id} className={i.id === selectedId ? "selected" : ""} onClick={() => onSelect(i.id)}>
              <td className="mono">{i.id}</td>
              <td>{i.title}</td>
              <td><span className={`badge sev-${i.severity}`}>{i.severity}</span></td>
              <td>{i.services.map((s) => <span key={s} className="chip">{s}</span>)}</td>
              <td><span className={`status status-${i.status}`}>{i.status}</span></td>
              <td className="muted">{timeAgo(i.created_at)}</td>
            </tr>
          ))}
          {incidents.length === 0 && (
            <tr><td colSpan="6" className="muted center">No incidents match the filters.</td></tr>
          )}
        </tbody>
      </table>
    </section>
  );
}

function IncidentDetail({ incident, suggestions, onAction, error }) {
  if (!incident) return <section className="panel detail muted center">Select an incident to see details.</section>;
  return (
    <section className="panel detail">
      <div className="detail-head">
        <div>
          <div className="mono muted">{incident.id}</div>
          <h2>{incident.title}</h2>
          <p>{incident.description}</p>
          <div>
            <span className={`badge sev-${incident.severity}`}>{incident.severity}</span>{" "}
            <span className={`status status-${incident.status}`}>{incident.status}</span>{" "}
            {incident.services.map((s) => <span key={s} className="chip">{s}</span>)}
          </div>
        </div>
        <div className="actions">
          <button disabled={incident.status !== "open"} onClick={() => onAction("acknowledge")}>Acknowledge</button>
          <button className="primary" disabled={incident.status === "resolved"} onClick={() => onAction("resolve")}>Resolve</button>
        </div>
      </div>
      {error && <div className="error">{error}</div>}

      <h3>Suggested root causes</h3>
      <div className="suggestions">
        {suggestions.map((s) => (
          <div key={s.cause} className="suggestion">
            <div className="suggestion-head">
              <strong>{s.cause}</strong>
              <span className="muted">{Math.round(s.confidence * 100)}%</span>
            </div>
            <div className="bar"><div style={{ width: `${s.confidence * 100}%` }} /></div>
            <div className="action">→ {s.action}</div>
            {s.evidence.length > 0 && (
              <ul className="evidence">{s.evidence.map((e) => <li key={e} className="mono">{e}</li>)}</ul>
            )}
          </div>
        ))}
      </div>

      <h3>Timeline</h3>
      <ol className="timeline">
        {incident.timeline.map((t, idx) => (
          <li key={idx} className={`tl-${t.type}`}>
            <span className="muted mono">{fmtTime(t.timestamp)}</span> <strong>{t.type}</strong> — {t.message}
          </li>
        ))}
      </ol>

      <h3>Logs</h3>
      <div className="logs mono">
        {incident.logs.map((l, idx) => (
          <div key={idx} className={`log log-${l.level}`}>
            <span className="muted">{fmtTime(l.timestamp)}</span> <span className="lvl">{l.level}</span>{" "}
            <span className="svc">[{l.service}]</span> {l.message}
          </div>
        ))}
      </div>
    </section>
  );
}

export default function App() {
  const [incidents, setIncidents] = useState([]);
  const [stats, setStats] = useState(null);
  const [filters, setFilters] = useState({ status: "", severity: "" });
  const [selectedId, setSelectedId] = useState(null);
  const [incident, setIncident] = useState(null);
  const [suggestions, setSuggestions] = useState([]);
  const [error, setError] = useState(null);

  const refreshList = useCallback(async () => {
    const [list, s] = await Promise.all([api.listIncidents(filters), api.stats()]);
    setIncidents(list);
    setStats(s);
  }, [filters]);

  useEffect(() => {
    refreshList().catch((e) => setError(e.message));
  }, [refreshList]);

  useEffect(() => {
    if (!selectedId) return;
    setError(null);
    Promise.all([api.getIncident(selectedId), api.getSuggestions(selectedId)])
      .then(([inc, sug]) => { setIncident(inc); setSuggestions(sug); })
      .catch((e) => setError(e.message));
  }, [selectedId]);

  async function handleAction(action) {
    try {
      setError(null);
      setIncident(await api[action](selectedId));
      await refreshList();
    } catch (e) {
      setError(e.message);
    }
  }

  return (
    <div className="app">
      <header>
        <h1>🚨 Incident Monitor</h1>
        <span className="muted">Synthetic data · in-memory</span>
      </header>
      <SummaryCards stats={stats} />
      <main>
        <IncidentTable incidents={incidents} selectedId={selectedId} onSelect={setSelectedId}
          filters={filters} setFilters={setFilters} />
        <IncidentDetail incident={incident} suggestions={suggestions} onAction={handleAction} error={error} />
      </main>
    </div>
  );
}
