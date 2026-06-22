import { useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "../../services/axios";
import { getDashboardPath, isValidDepartment, setSession } from "../../utils/auth";
import "../../styles/components/login.css";

const DEMO_ACCOUNTS = [
  { department: "Warehouse", username: "demo_warehouse", password: "Demo@1234" },
  { department: "Repairs",   username: "demo_repairs",   password: "Demo@1234" },
  { department: "Stores",    username: "demo_stores",    password: "Demo@1234" },
  { department: "Finance",   username: "demo_finance",   password: "Demo@1234" },
];

export default function Login() {
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [activeDemo, setActiveDemo] = useState(null);

  const handleDemoSelect = (account) => {
    setUsername(account.username);
    setPassword(account.password);
    setActiveDemo(account.username);
    setError("");
  };

  const handleLogin = async () => {
    setError("");
    setLoading(true);

    try {
      const response = await api.post("/auth/login/", { username, password });
      const { access, refresh, department, full_name } = response.data;

      if (!isValidDepartment(department)) {
        setError("Your account has no valid department assigned. Contact an administrator.");
        return;
      }

      setSession({ access, refresh, department, full_name });

      const dashboardPath = getDashboardPath(department);
      navigate(dashboardPath, { replace: true });
    } catch {
      setError("Invalid username or password.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login">
      <div className="login__card">
        <h2 className="login__title">Sign in</h2>
        <p className="login__subtitle">OPS Staff Portal</p>

        {error && <p className="login__error">{error}</p>}

        <div className="login__field">
          <label className="login__label" htmlFor="username">
            Username
          </label>
          <input
            id="username"
            className="login__input"
            type="text"
            value={username}
            onChange={(e) => { setUsername(e.target.value); setActiveDemo(null); }}
            onKeyDown={(e) => e.key === "Enter" && handleLogin()}
            placeholder="Enter username"
          />
        </div>

        <div className="login__field">
          <label className="login__label" htmlFor="password">
            Password
          </label>
          <input
            id="password"
            className="login__input"
            type="password"
            value={password}
            onChange={(e) => { setPassword(e.target.value); setActiveDemo(null); }}
            onKeyDown={(e) => e.key === "Enter" && handleLogin()}
            placeholder="Enter password"
          />
        </div>

        <button className="login__btn" onClick={handleLogin} disabled={loading}>
          {loading ? "Signing in..." : "Sign in"}
        </button>

        {/* Demo Accounts Panel */}
        <div className="login__demo">
          <div className="login__demo-header">
            <span className="login__demo-label">Demo Access</span>
            <span className="login__demo-hint">Select a department to auto-fill credentials</span>
          </div>
          <div className="login__demo-grid">
            {DEMO_ACCOUNTS.map((account) => (
              <button
                key={account.username}
                className={`login__demo-card ${activeDemo === account.username ? "login__demo-card--active" : ""}`}
                onClick={() => handleDemoSelect(account)}
              >
                <span className="login__demo-dept">{account.department}</span>
                <span className="login__demo-user">{account.username}</span>
              </button>
            ))}
          </div>
          <p className="login__demo-note">
            Try signing in with a different department's credentials to see access control in action.
          </p>
        </div>
      </div>
    </div>
  );
}