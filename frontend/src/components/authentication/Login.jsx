import { useState } from "react";
import api from '../../services/axios';

const departmentRoutes = {
  hr: "/pages/HRPage",
  warehouse: "/pages/ClientPage",
};

export default function Login() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleLogin = async () => {
    setError("");
    setLoading(true);
    try {
      const response = await api.post("/auth/login/", { username, password });
      const { access, refresh, department, full_name } = response.data;

      localStorage.setItem("access", access);
      localStorage.setItem("refresh", refresh);
      localStorage.setItem("department", department);
      localStorage.setItem("full_name", full_name);

      const route = departmentRoutes[department] || "/dashboard";
      window.location.href = route;
    } catch (err) {
      setError("Invalid username or password.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", background: "#f5f5f4" }}>
      <div style={{ background: "#fff", padding: "2rem", borderRadius: "12px", border: "1px solid #e5e5e5", width: "100%", maxWidth: "380px" }}>

        <h2 style={{ marginBottom: "4px", fontSize: "20px", fontWeight: 600 }}>Sign in</h2>
        <p style={{ color: "#888", fontSize: "13px", marginBottom: "1.5rem" }}>OPS Staff Portal</p>

        {error && (
          <p style={{ color: "#b91c1c", background: "#fff1f1", border: "1px solid #fecaca", borderRadius: "8px", padding: "10px 12px", fontSize: "13px", marginBottom: "1rem" }}>
            {error}
          </p>
        )}

        <div style={{ marginBottom: "1rem" }}>
          <label style={{ fontSize: "13px", color: "#555", display: "block", marginBottom: "6px" }}>Username</label>
          <input
            type="text"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleLogin()}
            placeholder="Enter username"
            style={{ width: "100%", padding: "9px 12px", borderRadius: "8px", border: "1px solid #e5e5e5", fontSize: "14px", boxSizing: "border-box" }}
          />
        </div>

        <div style={{ marginBottom: "1.5rem" }}>
          <label style={{ fontSize: "13px", color: "#555", display: "block", marginBottom: "6px" }}>Password</label>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleLogin()}
            placeholder="Enter password"
            style={{ width: "100%", padding: "9px 12px", borderRadius: "8px", border: "1px solid #e5e5e5", fontSize: "14px", boxSizing: "border-box" }}
          />
        </div>

        <button
          onClick={handleLogin}
          disabled={loading}
          style={{ width: "100%", padding: "10px", background: "#111", color: "#fff", border: "none", borderRadius: "8px", fontSize: "14px", fontWeight: 500, cursor: loading ? "not-allowed" : "pointer", opacity: loading ? 0.7 : 1 }}
        >
          {loading ? "Signing in..." : "Sign in"}
        </button>

      </div>
    </div>
  );
}