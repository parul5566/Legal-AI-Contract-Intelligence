import React, { useEffect, useRef, useState } from "react";
import { api } from "../api.js";
import { fmtDate, fmtBytes, STATUS_STYLE } from "../constants.js";

export default function Documents() {
  const [docs, setDocs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");
  const [uploadMsg, setUploadMsg] = useState("");
  const fileRef = useRef(null);

  const load = (q = "") => {
    setLoading(true);
    api
      .get(`/api/documents${q ? `?q=${encodeURIComponent(q)}` : ""}`)
      .then((d) => setDocs(d.items))
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => load(search), [search]);

  const upload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploadMsg("");
    const fd = new FormData();
    fd.append("file", file);
    try {
      await api.post("/api/documents", fd);
      setUploadMsg(`Uploaded "${file.name}" — analysis started.`);
      load(search);
    } catch (err) {
      setUploadMsg(`Upload failed: ${err.message}`);
    }
    if (fileRef.current) fileRef.current.value = "";
  };

  const remove = async (id) => {
    if (!confirm("Delete this document and all its analysis?")) return;
    try {
      await api.del(`/api/documents/${id}`);
      load(search);
    } catch (err) {
      setError(err.message);
    }
  };

  return (
    <div>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
        }}
      >
        <div>
          <h1>Documents</h1>
          <p className="sub">Upload contracts and manage analysis.</p>
        </div>
        <div>
          <input
            ref={fileRef}
            type="file"
            accept=".pdf,.docx,.txt"
            onChange={upload}
            style={{ width: "auto" }}
          />
        </div>
      </div>

      {uploadMsg && <div className="ok">{uploadMsg}</div>}
      {error && <div className="err">{error}</div>}

      <div className="toolbar">
        <div>
          <label className="fld">Search</label>
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Document name…"
          />
        </div>
      </div>

      {loading ? (
        <div className="spin">⏳</div>
      ) : docs.length === 0 ? (
        <div className="card empty">
          No documents yet. Upload a PDF, DOCX, or TXT contract above.
        </div>
      ) : (
        <table className="tbl">
          <thead>
            <tr>
              <th>Document</th>
              <th>Type</th>
              <th>Size</th>
              <th>Status</th>
              <th>Created</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {docs.map((d) => (
              <tr key={d.id}>
                <td>
                  <a href={`#/documents/${d.id}`} style={{ fontWeight: 600 }}>
                    {d.original_name}
                  </a>
                  {d.title && d.title !== d.original_name && (
                    <div className="muted" style={{ fontSize: 12 }}>
                      {d.title}
                    </div>
                  )}
                </td>
                <td>{d.doc_type || "—"}</td>
                <td className="muted">{fmtBytes(d.size_bytes)}</td>
                <td>
                  <span
                    className="badge"
                    style={{ background: STATUS_STYLE[d.status] || "#999" }}
                  >
                    {d.status}
                  </span>
                  {d.error && (
                    <div className="muted" style={{ fontSize: 11, marginTop: 2 }}>
                      {d.error.slice(0, 80)}
                    </div>
                  )}
                </td>
                <td className="muted">{fmtDate(d.created_at)}</td>
                <td>
                  <button
                    className="btn small danger"
                    onClick={() => remove(d.id)}
                  >
                    Delete
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
