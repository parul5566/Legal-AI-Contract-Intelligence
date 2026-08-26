import React, { useEffect, useState } from "react";
import { api } from "../api.js";
import { fmtDate, STATUS_STYLE, clauseLabel, riskLabel, SEVERITY_ORDER } from "../constants.js";

const SEV_COLORS = { critical: "#991b1b", high: "#dc2626", medium: "#f59e0b", low: "#3b82f6" };
const SEV_ICONS = { critical: "🔴", high: "🟠", medium: "🟡", low: "🔵" };

/* ── SVG Donut Chart ─ */
function Donut({ data, colors, size = 180, stroke = 28, label = "Risks" }) {
  const total = Object.values(data).reduce((a, b) => a + b, 0) || 1;
  const radius = (size - stroke) / 2;
  const circ = 2 * Math.PI * radius;
  let offset = 0;
  return (
    <svg width={size} height={size} style={{ transform: "rotate(-90deg)" }}>
      <circle cx={size / 2} cy={size / 2} r={radius} fill="none" stroke="#e5e7eb" strokeWidth={stroke} />
      {SEVERITY_ORDER.map((sev) => {
        const val = data[sev] || 0;
        if (!val) return null;
        const dash = (val / total) * circ;
        const el = (
          <circle
            key={sev}
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            stroke={colors[sev]}
            strokeWidth={stroke}
            strokeDasharray={`${dash} ${circ - dash}`}
            strokeDashoffset={-offset}
            strokeLinecap="butt"
            style={{ transition: "stroke-dasharray .6s ease" }}
          />
        );
        offset += dash;
        return el;
      })}
      <text
        x={size / 2}
        y={size / 2}
        textAnchor="middle"
        dominantBaseline="central"
        fill="#1e293b"
        fontSize="28"
        fontWeight="800"
        style={{ transform: "rotate(90deg)", transformOrigin: "center" }}
      >
        {total}
      </text>
    </svg>
  );
}

/* ── SVG Gauge (health score) ─ */
function Gauge({ value, size = 160 }) {
  const pct = Math.max(0, Math.min(100, value || 0));
  const r = 70;
  const circ = Math.PI * r;
  const dash = (pct / 100) * circ;
  const color = pct >= 70 ? "#16a34a" : pct >= 40 ? "#f59e0b" : "#dc2626";
  return (
    <svg width={size} height={size * 0.65} viewBox="0 0 160 104">
      <path d={`M 10 90 A ${r} ${r} 0 0 1 150 90`} fill="none" stroke="#e5e7eb" strokeWidth="12" strokeLinecap="round" />
      <path
        d={`M 10 90 A ${r} ${r} 0 0 1 150 90`}
        fill="none"
        stroke={color}
        strokeWidth="12"
        strokeLinecap="round"
        strokeDasharray={`${dash} ${circ}`}
        style={{ transition: "stroke-dasharray .8s ease" }}
      />
      <text x="80" y="78" textAnchor="middle" fill="#1e293b" fontSize="30" fontWeight="800">
        {pct}
      </text>
      <text x="80" y="98" textAnchor="middle" fill="#94a3b8" fontSize="10" fontWeight="600">
        HEALTH SCORE
      </text>
    </svg>
  );
}

/* ── Horizontal Bar (clause categories) ─ */
function BarRow({ label, value, max, color }) {
  const pct = max ? (value / max) * 100 : 0;
  return (
    <div className="barrow">
      <div className="barrow-label">{label}</div>
      <div className="barrow-track">
        <div className="barrow-fill" style={{ width: `${pct}%`, background: color }} />
      </div>
      <div className="barrow-value">{value}</div>
    </div>
  );
}

/* ── KPI Card ─ */
function KpiCard({ icon, label, value, sub, accent }) {
  return (
    <div className={`kpi-card ${accent || ""}`}>
      <div className="kpi-icon">{icon}</div>
      <div className="kpi-body">
        <div className="kpi-value">{value}</div>
        <div className="kpi-label">{label}</div>
        {sub && <div className="kpi-sub">{sub}</div>}
      </div>
    </div>
  );
}

export default function Dashboard() {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .get("/api/stats/dashboard")
      .then(setStats)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading)
    return (
      <div className="dash-load">
        <div className="spin" style={{ fontSize: 32 }}>⏳</div>
        <p className="muted">Loading dashboard…</p>
      </div>
    );
  if (error) return <div className="err">{error}</div>;

  const sevTotal = Object.values(stats.severity_histogram || {}).reduce((a, b) => a + b, 0);
  const clauseEntries = Object.entries(stats.clause_category_counts || {}).sort((a, b) => b[1] - a[1]);
  const clauseMax = Math.max(...clauseEntries.map(([, n]) => n), 1);
  const riskEntries = Object.entries(stats.risk_category_counts || {}).sort((a, b) => b[1] - a[1]);
  const riskMax = Math.max(...riskEntries.map(([, n]) => n), 1);
  const docsHealth = stats.documents_health || [];
  const healthBuckets = { poor: 0, fair: 0, good: 0 };
  docsHealth.forEach((d) => {
    if (d.health_score < 40) healthBuckets.poor++;
    else if (d.health_score < 70) healthBuckets.fair++;
    else healthBuckets.good++;
  });

  return (
    <div className="dash-page">
      {/* ── Header ─ */}
      <div className="dash-header">
        <div>
          <h1 className="dash-title">Contract Intelligence Dashboard</h1>
          <p className="dash-subtitle">
            Real-time overview of documents, clauses, risks, and contract health
          </p>
        </div>
        <div className="dash-header-right">
          <span className="dash-pill">
            <span className="dot-live" /> Live
          </span>
          <span className="dash-date">{new Date().toLocaleDateString(undefined, { weekday: "long", month: "long", day: "numeric" })}</span>
        </div>
      </div>

      {/* ── KPI Row ─ */}
      <div className="kpi-grid">
        <KpiCard icon="📄" label="Total Documents" value={stats.total_documents} sub={`${stats.ready_documents} analyzed · ${stats.failed_documents} failed`} accent="blue" />
        <KpiCard icon="⚠️" label="High-Risk Contracts" value={stats.high_risk_documents} sub={`${stats.total_risks} total risk findings`} accent="red" />
        <KpiCard icon="📋" label="Clauses Extracted" value={stats.total_clauses} sub={`${clauseEntries.length} categories detected`} accent="purple" />
        <KpiCard icon="⚖️" label="Comparisons" value={stats.total_comparisons} sub="Contract version diffs" accent="green" />
        <KpiCard icon="🔍" label="Pending Reviews" value={stats.pending_reviews} sub="Awaiting analyst action" accent="orange" />
        <KpiCard icon="👥" label="Active Users" value={stats.active_users} sub="With platform access" accent="teal" />
      </div>

      {/* ── Charts Row ─ */}
      <div className="dash-grid-3">
        {/* Risk Severity Donut */}
        <div className="card chart-card">
          <div className="card-head">
            <h3>Risk Severity Distribution</h3>
            <span className="card-badge">{sevTotal} total</span>
          </div>
          <div className="donut-wrap">
            <Donut data={stats.severity_histogram} colors={SEV_COLORS} />
            <div className="donut-legend">
              {SEVERITY_ORDER.map((sev) => {
                const n = stats.severity_histogram?.[sev] || 0;
                const pct = sevTotal ? Math.round((n / sevTotal) * 100) : 0;
                return (
                  <div key={sev} className="legend-row">
                    <span className="legend-dot" style={{ background: SEV_COLORS[sev] }} />
                    <span className="legend-label">{SEV_ICONS[sev]} {sev.charAt(0).toUpperCase() + sev.slice(1)}</span>
                    <span className="legend-count">{n}</span>
                    <span className="legend-pct">{pct}%</span>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* Average Health Gauge */}
        <div className="card chart-card">
          <div className="card-head">
            <h3>Portfolio Health</h3>
            <span className="card-badge">{docsHealth.length} docs</span>
          </div>
          <div className="gauge-wrap">
            <Gauge value={stats.avg_health_score} />
            <div className="gauge-stats">
              <div className="gauge-stat-row">
                <span className="dot-sm" style={{ background: "#dc2626" }} /> Poor (&lt;40)
                <b>{healthBuckets.poor}</b>
              </div>
              <div className="gauge-stat-row">
                <span className="dot-sm" style={{ background: "#f59e0b" }} /> Fair (40–69)
                <b>{healthBuckets.fair}</b>
              </div>
              <div className="gauge-stat-row">
                <span className="dot-sm" style={{ background: "#16a34a" }} /> Good (70+)
                <b>{healthBuckets.good}</b>
              </div>
            </div>
          </div>
        </div>

        {/* Risk Categories */}
        <div className="card chart-card">
          <div className="card-head">
            <h3>Risk Categories</h3>
            <span className="card-badge">{riskEntries.length} types</span>
          </div>
          <div className="bar-list">
            {riskEntries.length === 0 && <p className="muted">No risks identified yet.</p>}
            {riskEntries.slice(0, 8).map(([cat, n]) => (
              <BarRow key={cat} label={riskLabel(cat)} value={n} max={riskMax} color="#ef4444" />
            ))}
          </div>
        </div>
      </div>

      {/* ── Clause Categories + Health by Document ─ */}
      <div className="dash-grid-2">
        <div className="card">
          <div className="card-head">
            <h3>Clause Categories Detected</h3>
            <span className="card-badge">{clauseEntries.length} / 17</span>
          </div>
          <div className="bar-list">
            {clauseEntries.length === 0 && <p className="muted">No clauses detected yet.</p>}
            {clauseEntries.map(([cat, n], i) => (
              <BarRow
                key={cat}
                label={clauseLabel(cat)}
                value={n}
                max={clauseMax}
                color={`hsl(${(i * 25) % 360}, 65%, 50%)`}
              />
            ))}
          </div>
        </div>

        <div className="card">
          <div className="card-head">
            <h3>Document Health Scores</h3>
          </div>
          {docsHealth.length === 0 && <p className="muted">No analyzed documents yet.</p>}
          <div className="health-doc-list">
            {docsHealth.map((d) => (
              <div
                key={d.document_id}
                className="health-doc-row"
                onClick={() => (location.hash = `#/documents/${d.document_id}`)}
              >
                <div className="health-doc-name" title={d.title}>{d.title}</div>
                <div className="health-doc-bar">
                  <div
                    className="health-doc-fill"
                    style={{
                      width: `${d.health_score}%`,
                      background: d.health_score >= 70 ? "#16a34a" : d.health_score >= 40 ? "#f59e0b" : "#dc2626",
                    }}
                  />
                </div>
                <div className="health-doc-score" style={{ color: d.health_score >= 70 ? "#16a34a" : d.health_score >= 40 ? "#f59e0b" : "#dc2626" }}>
                  {d.health_score}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* ── Recent Documents Table ─ */}
      <div className="card">
        <div className="card-head">
          <h3>Recent Documents</h3>
          <a href="#/documents" className="card-link">View all →</a>
        </div>
        <div className="tbl-wrap">
        <table className="tbl dash-tbl">
          <thead>
            <tr>
              <th>Document</th>
              <th>Type</th>
              <th>Status</th>
              <th>Parties</th>
              <th>Jurisdiction</th>
              <th>Created</th>
            </tr>
          </thead>
          <tbody>
            {stats.recent_documents.map((d) => {
              const h = docsHealth.find((x) => x.document_id === d.id);
              return (
                <tr key={d.id} className="dash-row" onClick={() => (location.hash = `#/documents/${d.id}`)}>
                  <td>
                    <div className="doc-name-cell">
                      <span className="doc-icon">📄</span>
                      <div>
                        <div className="doc-name">{d.original_name}</div>
                        {h && (
                          <div className="doc-health-mini">
                            <span className="dot-sm" style={{ background: h.health_score >= 70 ? "#16a34a" : h.health_score >= 40 ? "#f59e0b" : "#dc2626" }} />
                            Health: {h.health_score}/100
                          </div>
                        )}
                      </div>
                    </div>
                  </td>
                  <td>
                    <span className="type-badge">{d.doc_type || "—"}</span>
                  </td>
                  <td>
                    <span className="status-badge" style={{ background: STATUS_STYLE[d.status] || "#999" }}>
                      {d.status}
                    </span>
                  </td>
                  <td className="muted" style={{ maxWidth: 200, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                    {d.parties?.join(", ") || "—"}
                  </td>
                  <td className="muted">{d.jurisdiction || "—"}</td>
                  <td className="muted">{fmtDate(d.created_at)}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
        </div>
      </div>
    </div>
  );
}
