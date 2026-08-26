const TOKEN_KEY = "legalai_token";
const USER_KEY = "legalai_user";

export function getToken() {
  return localStorage.getItem(TOKEN_KEY) || "";
}
export function getUser() {
  try {
    return JSON.parse(localStorage.getItem(USER_KEY) || "null");
  } catch {
    return null;
  }
}
export function setSession(token, user) {
  localStorage.setItem(TOKEN_KEY, token);
  localStorage.setItem(USER_KEY, JSON.stringify(user));
}
export function clearSession() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
}

async function request(path, opts = {}) {
  const headers = { ...(opts.headers || {}) };
  if (opts.body && !(opts.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
  }
  const token = getToken();
  if (token) headers["Authorization"] = `Bearer ${token}`;
  const res = await fetch(path, { ...opts, headers });
  if (res.status === 401) {
    clearSession();
    if (!location.hash.startsWith("#/login")) location.hash = "#/login";
    throw new Error("Not authenticated");
  }
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const j = await res.json();
      detail = typeof j.detail === "string" ? j.detail : JSON.stringify(j.detail);
    } catch {
      /* ignore */
    }
    throw new Error(detail || `HTTP ${res.status}`);
  }
  if (res.status === 204) return null;
  return res.json();
}

export const api = {
  get: (p) => request(p),
  post: (p, body) =>
    request(p, { method: "POST", body: body instanceof FormData ? body : JSON.stringify(body) }),
  del: (p) => request(p, { method: "DELETE" }),
};

export async function login(email, password) {
  const res = await fetch("/api/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) {
    const j = await res.json().catch(() => ({}));
    throw new Error(j.detail || "Login failed");
  }
  return res.json();
}

export async function register(email, name, password) {
  const res = await fetch("/api/auth/register", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, name, password, role: "analyst" }),
  });
  if (!res.ok) {
    const j = await res.json().catch(() => ({}));
    throw new Error(j.detail || "Registration failed");
  }
  return res.json();
}
