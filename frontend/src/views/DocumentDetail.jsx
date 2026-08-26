import React, { useEffect, useState, useCallback } from "react";
import { api } from "../api.js";
import {
  fmtDate,
  STATUS_STYLE,
  clauseLabel,
  riskLabel,
  SEVERITY_ORDER,
  SEV_STYLE,
} from "../constants.js";

export default function DocumentDetail({ id }) {
  const [doc, setDoc] = useState(null);
  const [tab, setTab] = useState("document");
  const [clauses, setClauses] = useState([]);
  const [risks, setRisks] = useState([]);
  const [summary, setSummary] = useState(null);
  const [sections, setSections] = useState([]);
  const [reviewLog, setReviewLog] = useState([]);
  const [error, setError] = useState("");
  const [clauseFilter, setClauseFilter] = useState("");
  const [riskFilter, setRiskFilter] = useState("");
  const [msg, setMsg] = useState("");

  const reload = useCallback(() => {
    api.get(`/api/documents/${id}`).then(setDoc).catch((e) => setError(e.message));
    api
      .get(`/api/documents/${id}/clauses`)
      .then(setClauses)
      .catch(() => setClauses([]));
    api
      .get(`/api/documents/${id}/risks`)
      .then(setRisks)
      .catch(() => setRisks([]));
    api
      .get(`/api/documents/${id}/summary`)
      .then(setSummary)
      .catch(() => setSummary(null));
    api
      .get(`/api/documents/${id}/sections`)
      .then(setSections)
      .catch(() => setSections([]));
    api
      .get(`/api/documents/${id}/review-log`)
      .then(setReviewLog)
      .catch(() => setReviewLog([]));
  }, [id]);

  useEffect(() => {
    reload();
    const poll = setInterval(() => {
      api.get(`/api/documents/${id}/status`).then((s) => {
        setDoc((d) => (d ? { ...d, status: s.status, error: s.error } : d));
        if (s.status === "ready" || s.status === "failed") clearInterval(poll);
      });
    }, 4000);
    return () => clearInterval(poll);
  }, [id, reload]);

  const reanalyze = async () => {
    setMsg("Re-analysis queued…");
    await api.post(`/api/documents/${id}/analyze`);
  };

  const regenSummary = async () => {
    setMsg("Regenerating summary…");
    try {
      const s = await api.post(`/api/documents/${id}/summary/regenerate`);
      setSummary(s);
      setMsg("Summary regenerated.");
    } catch (e) {
      setMsg(e.message);
    }
  };

  const reviewClause = async (cid, action, category) => {
    try {
      await api.post(`/api/clauses/${cid}/review`, { action, category });
      reload();
    } catch (e) {
      setMsg(e.message);
    }
  };

  const reviewRisk = async (rid, action) => {
    try {
      await api.post(`/api/risks/${rid}/review`, { action });
      reload();
    } catch (e) {
      setMsg(e.message);
    }
  };

  if (error) return <div className="err">{error}</div>;
  if (!doc)
    return (
      <div className="spin">⏳</div>
    );

  const isReady = doc.status === "ready";
  const isPending = ["pending", "parsing", "analyzing"].includes(doc.status);

  const categories = [...new Set(clauses.map((c) => c.category))].sort();

  const filteredClauses = clauseFilter
    ? clauses.filter((c) => c.category === clauseFilter)
    : clauses;
  const filteredRisks = riskFilter
    ? risks.filter((r) => r.severity === riskFilter)
    : risks;

  const healthColor =
    summary?.health_score >= 75
      ? "#16a34a"
      : summary?.health_score >= 50
      ? "#d97706"
      : "#dc2626";

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between" }}>
        <div>
          <h1>{doc.original_name}</h1>
          <p className="sub">
            {doc.doc_type || "Contract"} ·{" "}
            {doc.parties?.length ? doc.parties.join(" ↔ ") : "Parties unknown"} ·{" "}
            {doc.jurisdiction || "Jurisdiction —"} ·{" "}
            {doc.page_count} pages
          </p>
        </div>
        <div style={{ textAlign: "right" }}>
          <span
            className="badge"
            style={{
              background: STATUS_STYLE[doc.status] || "#999",
              fontSize: 13,
              padding: "5px 12px",
            }}
          >
            {doc.status}
          </span>
          <div style={{ marginTop: 8 }}>
            <button className="btn small" onClick={reanalyze} disabled={isPending}>
              {isPending ? "Analyzing…" : "Re-analyze"}
            </button>
          </div>
        </div>
      </div>

      {doc.error && <div className="err">Analysis error: {doc.error}</div>}
      {msg && <div className="ok">{msg}</div>}

      {isPending && (
        <div className="card" style={{ textAlign: "center" }}>
          <span className="spin">⏳</span> Analysis in progress… This page will
          update automatically.
        </div>
      )}

      <div className="tabs">
        <button
          className={tab === "document" ? "active" : ""}
          onClick={() => setTab("document")}
        >
          Document
        </button>
        <button
          className={tab === "clauses" ? "active" : ""}
          onClick={() => setTab("clauses")}
        >
          Clauses ({clauses.length})
        </button>
        <button
          className={tab === "risks" ? "active" : ""}
          onClick={() => setTab("risks")}
        >
          Risks ({risks.length})
        </button>
        <button
          className={tab === "summary" ? "active" : ""}
          onClick={() => setTab("summary")}
        >
          Summary
        </button>
        <button
          className={tab === "review" ? "active" : ""}
          onClick={() => setTab("review")}
        >
          Review Log ({reviewLog.length})
        </button>
        <button
          className={tab === "export" ? "active" : ""}
          onClick={() => setTab("export")}
        >
          Export
        </button>
      </div>

      {tab === "document" && (
        <div>
          <div className="card">
            <strong>Metadata</strong>
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "1fr 1fr",
                gap: 6,
                marginTop: 8,
                fontSize: 13.5,
              }}
            >
              <div>
                <strong>Title:</strong> {doc.title || "—"}
              </div>
              <div>
                <strong>Type:</strong> {doc.doc_type || "—"}
              </div>
              <div>
                <strong>Effective:</strong> {doc.effective_date || "—"}
              </div>
              <div>
                <strong>Expiry:</strong> {doc.expiry_date || "—"}
              </div>
              <div>
                <strong>Jurisdiction:</strong> {doc.jurisdiction || "—"}
              </div>
              <div>
                <strong>Characters:</strong> {doc.char_count.toLocaleString()}
              </div>
            </div>
          </div>
          <h2>Document Text ({sections.length} sections)</h2>
          <div className="card">
            {sections.map((s) => (
              <div key={s.id} style={{ marginBottom: 16 }}>
                {s.heading && (
                  <div style={{ fontWeight: 700, marginBottom: 4 }}>
                    {s.heading}
                  </div>
                )}
                <div className="docviewer">{s.body}</div>
              </div>
            ))}
            {sections.length === 0 && (
              <p className="muted">
                No sections detected. Document may still be processing.
              </p>
            )}
          </div>
        </div>
      )}

      {tab === "clauses" && (
        <div>
          <div className="toolbar">
            <div>
              <label className="fld">Filter by category</label>
              <select
                value={clauseFilter}
                onChange={(e) => setClauseFilter(e.target.value)}
              >
                <option value="">All ({clauses.length})</option>
                {categories.map((c) => (
                  <option key={c} value={c}>
                    {clauseLabel(c)}
                  </option>
                ))}
              </select>
            </div>
          </div>
          {filteredClauses.length === 0 ? (
            <div className="card empty">No clauses detected.</div>
          ) : (
            filteredClauses.map((c) => (
              <div key={c.id} className="card clausecard">
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "start",
                  }}
                >
                  <div>
                    <span className="cat">{clauseLabel(c.category)}</span>
                    {c.title && c.title !== c.category && (
                      <span className="muted"> — {c.title}</span>
                    )}
                  </div>
                  <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
                    <span
                      className="tag"
                      title="Confidence"
                    >
                      {Math.round(c.confidence * 100)}%
                    </span>
                    <span className="tag">p.{c.page}</span>
                    <span
                      className="tag"
                      style={{
                        background:
                          c.review_status === "accepted"
                            ? "#dcfce7"
                            : c.review_status === "rejected"
                            ? "#fee2e2"
                            : c.review_status === "corrected"
                            ? "#fef9c3"
                            : "#eef2f7",
                      }}
                    >
                      {c.review_status}
                    </span>
                  </div>
                </div>
                <div className="txt">{c.text}</div>
                <div style={{ display: "flex", gap: 6 }}>
                  <button
                    className="btn small"
                    onClick={() => reviewClause(c.id, "accept")}
                  >
                    Accept
                  </button>
                  <button
                    className="btn small ghost"
                    onClick={() => reviewClause(c.id, "reject")}
                  >
                    Reject
                  </button>
                  <button
                    className="btn small ghost"
                    onClick={() => reviewClause(c.id, "flag")}
                  >
                    Flag
                  </button>
                </div>
              </div>
            ))
          )}
        </div>
      )}

      {tab === "risks" && (
        <div>
          <div className="toolbar">
            <div>
              <label className="fld">Filter by severity</label>
              <select
                value={riskFilter}
                onChange={(e) => setRiskFilter(e.target.value)}
              >
                <option value="">All ({risks.length})</option>
                {SEVERITY_ORDER.map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </select>
            </div>
          </div>
          {filteredRisks.length === 0 ? (
            <div className="card empty">No risks identified.</div>
          ) : (
            filteredRisks.map((r) => {
              const st = SEV_STYLE[r.severity] || { bg: "#666", label: r.severity };
              return (
                <div key={r.id} className="card riskcard" style={{ borderLeftColor: st.bg }}>
                  <div
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "start",
                    }}
                  >
                    <div>
                      <span className="badge" style={{ background: st.bg }}>
                        {st.label}
                      </span>{" "}
                      <strong>{r.title}</strong>
                      <div className="muted" style={{ marginTop: 2 }}>
                        {riskLabel(r.category)}
                      </div>
                    </div>
                    <span
                      className="tag"
                      style={{
                        background:
                          r.review_status === "accepted"
                            ? "#dcfce7"
                            : r.review_status === "rejected"
                            ? "#fee2e2"
                            : "#eef2f7",
                      }}
                    >
                      {r.review_status}
                    </span>
                  </div>
                  <div style={{ marginTop: 8, fontSize: 13.5 }}>
                    <strong>Explanation:</strong> {r.explanation}
                  </div>
                  <div style={{ fontSize: 13.5, marginTop: 6 }}>
                    <strong>Suggested review:</strong> {r.suggestion}
                  </div>
                  {r.evidence && (
                    <div
                      style={{
                        fontSize: 12.5,
                        marginTop: 6,
                        color: "#475569",
                        background: "#f8fafc",
                        padding: 6,
                        borderRadius: 5,
                      }}
                    >
                      <strong>Evidence:</strong> {r.evidence.slice(0, 300)}
                    </div>
                  )}
                  <div style={{ display: "flex", gap: 6, marginTop: 8 }}>
                    <button
                      className="btn small"
                      onClick={() => reviewRisk(r.id, "accept")}
                    >
                      Accept
                    </button>
                    <button
                      className="btn small ghost"
                      onClick={() => reviewRisk(r.id, "reject")}
                    >
                      Reject
                    </button>
                    <button
                      className="btn small ghost"
                      onClick={() => reviewRisk(r.id, "flag")}
                    >
                      Flag
                    </button>
                  </div>
                </div>
              );
            })
          )}
        </div>
      )}

      {tab === "summary" && (
        <div>
          {summary ? (
            <>
              <div className="card">
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    marginBottom: 8,
                  }}
                >
                  <strong>Contract Health Score</strong>
                  <button className="btn small ghost" onClick={regenSummary}>
                    Regenerate
                  </button>
                </div>
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 12,
                  }}
                >
                  <div style={{ fontSize: 32, fontWeight: 700, color: healthColor }}>
                    {summary.health_score}
                  </div>
                  <div style={{ flex: 1 }}>
                    <div className="healthbar">
                      <div
                        style={{
                          width: `${summary.health_score}%`,
                          background: healthColor,
                        }}
                      />
                    </div>
                    <div className="muted" style={{ marginTop: 4 }}>
                      {summary.health_verdict}
                    </div>
                  </div>
                </div>
                <div className="muted" style={{ marginTop: 4 }}>
                  Model: {summary.model}
                </div>
              </div>

              <div className="card">
                <strong>Executive Summary</strong>
                <p style={{ fontSize: 14, lineHeight: 1.6 }}>
                  {summary.executive}
                </p>
              </div>

              <div className="grid cols2">
                <div className="card">
                  <strong>Key Obligations</strong>
                  <SummaryList items={summary.key_obligations} />
                </div>
                <div className="card">
                  <strong>Payments</strong>
                  <SummaryList items={summary.payments} />
                </div>
                <div className="card">
                  <strong>Important Dates</strong>
                  <SummaryList items={summary.important_dates} />
                </div>
                <div className="card">
                  <strong>Major Risks</strong>
                  <SummaryList items={summary.major_risks} />
                </div>
                <div className="card">
                  <strong>Termination</strong>
                  <p style={{ fontSize: 13.5 }}>{summary.termination}</p>
                </div>
                <div className="card">
                  <strong>Restrictions</strong>
                  <SummaryList items={summary.restrictions} />
                </div>
                <div className="card">
                  <strong>Compliance</strong>
                  <SummaryList items={summary.compliance} />
                </div>
              </div>
            </>
          ) : (
            <div className="card empty">
              {isReady
                ? "No summary available. Click Re-analyze."
                : "Document is still being analyzed."}
            </div>
          )}
        </div>
      )}

      {tab === "review" && (
        <div>
          {reviewLog.length === 0 ? (
            <div className="card empty">No review actions yet.</div>
          ) : (
            <table className="tbl">
              <thead>
                <tr>
                  <th>Action</th>
                  <th>Target</th>
                  <th>Detail</th>
                  <th>When</th>
                </tr>
              </thead>
              <tbody>
                {reviewLog.map((r) => (
                  <tr key={r.id}>
                    <td>
                      <span className="tag">{r.action}</span>
                    </td>
                    <td>
                      {r.target_type} #{r.target_id}
                    </td>
                    <td className="muted">{r.detail || "—"}</td>
                    <td className="muted">{fmtDate(r.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      {tab === "export" && (
        <div>
          <div className="card">
            <p>
              Generate a self-contained HTML report of this document's clauses,
              risks, and AI summary.
            </p>
            <a
              className="btn"
              href={`/api/documents/${id}/export`}
              target="_blank"
              rel="noopener"
            >
              Open Export Report
            </a>
          </div>
        </div>
      )}
    </div>
  );
}

function SummaryList({ items }) {
  if (!items || items.length === 0)
    return <p className="muted">None detected.</p>;
  return (
    <ul style={{ margin: "8px 0 0", paddingLeft: 18, fontSize: 13.5 }}>
      {items.map((x, i) => (
        <li key={i} style={{ marginBottom: 4 }}>
          {x}
        </li>
      ))}
    </ul>
  );
}
