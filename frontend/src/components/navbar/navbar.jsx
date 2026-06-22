import { useNavigate } from "react-router-dom";
import api from "../../services/axios";
import { clearSession } from "../../utils/auth";
import "../../styles/components/navbar.css";

export default function Navbar({ fullName, department }) {
  const navigate = useNavigate();

  const handleLogout = async () => {
    const refresh = localStorage.getItem("refresh");
    try {
      await api.post("/auth/logout/", { refresh });
    } catch {
      // token may already be invalid — still clear and redirect
    } finally {
      clearSession();
      navigate("/login", { replace: true });
    }
  };

  const canReceiveNotifications = department === "repairs";

  return (
    <nav className="navbar">
      <span className="navbar__brand">OPS System</span>

      <div className="navbar__right">
        <button
          className={`navbar__bell ${!canReceiveNotifications ? "navbar__bell--disabled" : ""}`}
          disabled={!canReceiveNotifications}
          title={!canReceiveNotifications ? "Notifications not available for your department" : "Notifications"}
        >
          🔔
        </button>

        <div className="navbar__user">
          <span className="navbar__fullname">{fullName}</span>
          <span className="navbar__department">{department}</span>
        </div>

        <button className="navbar__signout" onClick={handleLogout}>
          Sign out
        </button>
      </div>
    </nav>
  );
}