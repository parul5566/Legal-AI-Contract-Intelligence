import React, { useEffect, useState, useCallback } from "react";
import { api, getToken, getUser, clearSession } from "./api.js";
import Login from "./views/Login.jsx";
import Dashboard from "./views/Dashboard.jsx";
import Documents from "./views/Documents.jsx";
import DocumentDetail from "./views/DocumentDetail.jsx";
import Compare from "./views/Compare.jsx";
import Audit from "./views/Audit.jsx";

function useHashRoute() {
  const [hash, setHash] = useState(location.hash || "#/");
  useEffect(() => {
    const onChange = () => setHash(location.hash || "#/");
    window.addEventListener("hashchange", onChange);
    return () => window.removeEventListener("hashchange", onChange);
  }, []);
  return hash;
}

const NAV_ITEMS = [
  { hash: "#/",         label: "Dashboard", icon: "📊", match: (r) => r === "#/" || r === "#", adminOnly: false },
  { hash: "#/documents", label: "Documents", icon: "📄", match: (r) => r.startsWith("#/documents"), adminOnly: false },
  { hash: "#/compare",   label: "Compare",   icon: "⚖️", match: (r) => r.startsWith("#/compare"),   adminOnly: false },
  { hash: "#/audit",     label: "Audit Log", icon: "📜", match: (r) => r.startsWith("#/audit"),     adminOnly: true  },
];

export default function App() {
  const route = useHashRoute();
  const [user, setUser] = useState(getUser());
  const [sidebarOpen, setSidebarOpen] = useState(false);

  useEffect(() => {
    if (!getToken() && !route.startsWith("#/login")) location.hash = "#/login";
  }, [route]);

  // Close sidebar on route change (mobile)
  useEffect(() => {
    setSidebarOpen(false);
  }, [route]);

  const logout = useCallback(() => {
    clearSession();
    setUser(null);
    location.hash = "#/login";
  }, []);

  if (!getToken()) {
    return <Login onAuth={(u) => setUser(u)} route={route} />;
  }

  const items = NAV_ITEMS.filter((i) => !i.adminOnly || user?.role === "admin");
  const current = items.find((i) => i.match(route));
  const pageTitle = current ? current.label : "Dashboard";

  let view = null;
  const docMatch = route.match(/^#\/documents\/(\d+)/);
  if (route === "#/" || route === "#") view = <Dashboard />;
  else if (docMatch) view = <DocumentDetail id={Number(docMatch[1])} />;
  else if (route.startsWith("#/documents")) view = <Documents />;
  else if (route.startsWith("#/compare")) view = <Compare />;
  else if (route.startsWith("#/audit")) view = user?.role === "admin" ? <Audit /> : <Dashboard />;
  else if (route.startsWith("#/login")) {
    location.hash = "#/";
    return null;
  } else view = <Dashboard />;

  return (
    <div className={`admin-layout ${sidebarOpen ? "sidebar-open" : ""}`}>
      {/* ── Mobile overlay ── */}
      <div className="sidebar-overlay" onClick={() => setSidebarOpen(false)} />

      {/* ── Sidebar ── */}
      <aside className="sidebar">
        <div className="sidebar-brand">
          <span className="brand-icon">⚖</span>
          <div className="brand-text">
            <div className="brand-name">Legal AI</div>
            <div className="brand-sub">Contract Intelligence</div>
          </div>
          <button className="sidebar-close" onClick={() => setSidebarOpen(false)}>✕</button>
        </div>

        <nav className="sidebar-nav">
          {items.map((item) => (
            <a
              key={item.hash}
              href={item.hash}
              className={`nav-item ${item.match(route) ? "active" : ""}`}
            >
              <span className="nav-icon">{item.icon}</span>
              <span className="nav-label">{item.label}</span>
              {item.match(route) && <span className="nav-active-bar" />}
            </a>
          ))}
        </nav>

        <div className="sidebar-footer">
          <div className="sidebar-user">
            <div className="user-avatar">{user?.name?.charAt(0)?.toUpperCase() || "U"}</div>
            <div className="user-info">
              <div className="user-name">{user?.name}</div>
              <div className="user-role">{user?.role}</div>
            </div>
          </div>
          <button className="btn-logout" onClick={logout}>
            <span>🚪</span> Sign out
          </button>
        </div>
      </aside>

      {/* ── Main area ── */}
      <div className="main-area">
        {/* Top bar */}
        <header className="topbar">
          <button className="hamburger" onClick={() => setSidebarOpen(true)}>
            <span /><span /><span />
          </button>
          <div className="topbar-title">{pageTitle}</div>
          <div className="topbar-right">
            <span className="topbar-user">{user?.name} · {user?.role}</span>
          </div>
        </header>

        {/* Disclaimer banner */}
        <div className="disclaimer">
          AI decision-support tool — not legal advice. Review all findings with qualified counsel.
        </div>

        {/* Page content */}
        <main className="content">{view}</main>
      </div>
    </div>
  );
}