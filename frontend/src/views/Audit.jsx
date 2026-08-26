import React, { useEffect, useState } from "react";
import { api } from "../api.js";
import { fmtDate } from "../constants.js";

export default function Audit() {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .get("/api/audit")
      .then((d) => setLogs(d.items))
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="spin">⏳</div>;
  if (error) return <div className="err">{error}</div>;

  return (
    <div>
      <h1>Audit Log</h1>
      <p className="sub">All user actions across the platform (admin only).</p>
      <table className="tbl">
        <thead>
          <tr>
            <th>Time</th>
            <th>User</th>
            <th>Event</th>
            <th>Entity</th>
            <th>Detail</th>
            <th>IP</th>
          </tr>
        </thead>
        <tbody>
          {logs.map((l) => (
            <tr key={l.id}>
              <td className="muted">{fmtDate(l.created_at)}</td>
              <td>{l.user_id || "—"}</td>
              <td>
                <span className="tag">{l.event}</span>
              </td>
              <td>
                {l.entity}
                {l.entity_id ? ` #${l.entity_id}` : ""}
              </td>
              <td className="muted">{l.detail || "—"}</td>
              <td className="muted">{l.ip}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
