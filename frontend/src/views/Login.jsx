import React, { useState } from "react";
import { login, register, setSession } from "../api.js";

export default function Login({ onAuth }) {
  const [mode, setMode] = useState("login");
  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  const submit = async (e) => {
    e.preventDefault();
    setError("");
    try {
      const data =
        mode === "login"
          ? await login(email, password)
          : await register(email, name, password);
      setSession(data.access_token, data.user);
      onAuth(data.user);
      location.hash = "#/";
    } catch (err) {
      setError(err.message);
    }
  };

  return (
    <div className="loginwrap">
      <div className="loginbox">
        <div className="logo">⚖️</div>
        <h1>Legal AI</h1>
        <p className="sub" style={{ textAlign: "center" }}>
          Contract Intelligence Platform
        </p>
        <div className="tabs" style={{ marginBottom: 14 }}>
          <button
            className={mode === "login" ? "active" : ""}
            onClick={() => setMode("login")}
          >
            Sign in
          </button>
          <button
            className={mode === "register" ? "active" : ""}
            onClick={() => setMode("register")}
          >
            Register
          </button>
        </div>
        <form onSubmit={submit}>
          {mode === "register" && (
            <div style={{ marginBottom: 12 }}>
              <label className="fld">Full name</label>
              <input
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
                minLength={2}
              />
            </div>
          )}
          <div style={{ marginBottom: 12 }}>
            <label className="fld">Email</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </div>
          <div style={{ marginBottom: 14 }}>
            <label className="fld">Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              minLength={8}
            />
          </div>
          {error && <div className="err">{error}</div>}
          <button className="btn" style={{ width: "100%" }} type="submit">
            {mode === "login" ? "Sign in" : "Create account"}
          </button>
        </form>
        <p className="muted" style={{ textAlign: "center", marginTop: 14 }}>
          Demo: admin@legalai.test / Admin@123
        </p>
      </div>
    </div>
  );
}
