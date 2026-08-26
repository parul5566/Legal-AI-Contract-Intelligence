import React, { useEffect, useState } from "react";
import { api } from "../api.js";
import { clauseLabel, fmtDate } from "../constants.js";

export default function Compare() {
  const [docs, setDocs] = useState([]);
  const [docA, setDocA] = useState("");
  const [docB, setDocB] = useState("");
  const [comparisons, setComparisons] = useState([]);
  const [active, setActive] = useState(null);
  const [error, setError] = useState("");

  const load = () => {
    api.get("/api/documents?status_filter=ready").then((d) => setDocs(d.items));
    api.get("/api/comparisons").then((d) => setComparisons(d.items));
  };

  useEffect(load, []);

  const create = async () => {
    setError("");
    if (!docA || !docB || docA === docB) {
      setError("Select two different documents.");
      return;
    }
    try {
      const c = await api.post("/api/comparisons", {
        doc_a_id: Number(docA),
        doc_b_id: Number(docB),
      });
      setActive(c);
      // poll
      const poll = setInterval(async () => {
        const fresh = await api.get(`/api/comparisons/${c.id}`);
        setActive(fresh);
        if (fresh.status === "ready" || fresh.status === "failed")
          clearInterval(poll);
      }, 3000);
      load();
    } catch (e) {
      setError(e.message);
    }
  };

  const kindLabel = { added: "🟢 Added", removed: "🔴 Removed", modified: "🟡 Modified" };

  return (
    <div>
      <h1>Contract Comparison</h1>
      <p className="sub">Compare two analyzed contracts side-by-side.</p>

      <div className="card">
        <div className="grid cols2">
          <div>
            <label className="fld">Contract A</label>
            <select value={docA} onChange={(e) => setDocA(e.target.value)}>
              <option value="">Select…</option>
              {docs.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.original_name}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="fld">Contract B</label>
            <select value={docB} onChange={(e) => setDocB(e.target.value)}>
              <option value="">Select…</option>
              {docs.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.original_name}
                </option>
              ))}
            </select>
          </div>
        </div>
        <div style={{ marginTop: 12 }}>
          <button className="btn" onClick={create}>
            Compare Contracts
          </button>
        </div>
        {error && <div className="err" style={{ marginTop: 10 }}>{error}</div>}
      </div>

      {active && active.status !== "ready" && (
        <div className="card" style={{ textAlign: "center" }}>
          <span className="spin">⏳</span> Comparison in progress…
        </div>
      )}

      {active && active.status === "ready" && (
        <div>
          <h2>Comparison Results ({active.changes?.length || 0} changes)</h2>
          {active.summary && (
            <div className="card">
              <pre
                style={{
                  whiteSpace: "pre-wrap",
                  fontFamily: "inherit",
                  fontSize: 13.5,
                  margin: 0,
                }}
              >
                {active.summary}
              </pre>
            </div>
          )}
          {active.changes?.map((c, i) => (
            <div key={i} className="card">
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  marginBottom: 8,
                }}
              >
                <div>
                  <strong>{kindLabel[c.kind]}</strong>{" "}
                  <span className="tag">{clauseLabel(c.category)}</span>
                </div>
                <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
                  {c.kind === "modified" && (
                    <>
                      <span className="tag">similarity {c.similarity.toFixed(2)}</span>
                      <span
                        className="tag"
                        style={{
                          background: c.material ? "#fef3c7" : "#dcfce7",
                        }}
                      >
                        {c.material ? "MATERIAL" : "minor"}
                      </span>
                    </>
                  )}
                </div>
              </div>
              <div className="muted" style={{ marginBottom: 6, fontSize: 12.5 }}>
                {c.rationale}
              </div>
              {c.kind === "modified" ? (
                <div className="diffrow">
                  <div className="diffbox removed">
                    <strong>Contract A:</strong>
                    {"\n\n"}
                    {c.text_a}
                  </div>
                  <div className="diffbox added">
                    <strong>Contract B:</strong>
                    {"\n\n"}
                    {c.text_b}
                  </div>
                </div>
              ) : c.kind === "added" ? (
                <div className="diffbox added">{c.text_b}</div>
              ) : (
                <div className="diffbox removed">{c.text_a}</div>
              )}
            </div>
          ))}
        </div>
      )}

      <h2>Past Comparisons</h2>
      {comparisons.length === 0 ? (
        <div className="card empty">No comparisons yet.</div>
      ) : (
        <table className="tbl">
          <thead>
            <tr>
              <th>ID</th>
              <th>Doc A</th>
              <th>Doc B</th>
              <th>Status</th>
              <th>Changes</th>
              <th>Created</th>
            </tr>
          </thead>
          <tbody>
            {comparisons.map((c) => (
              <tr
                key={c.id}
                style={{ cursor: "pointer" }}
                onClick={async () => {
                  const fresh = await api.get(`/api/comparisons/${c.id}`);
                  setActive(fresh);
                }}
              >
                <td>#{c.id}</td>
                <td>{c.doc_a_id}</td>
                <td>{c.doc_b_id}</td>
                <td>
                  <span className="tag">{c.status}</span>
                </td>
                <td>{c.changes?.length || 0}</td>
                <td className="muted">{fmtDate(c.created_at)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
