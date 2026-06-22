import { useNavigate } from "react-router-dom";
import api from "../../services/axios";
import { clearSession } from "../../utils/auth";

export default function Logout() {
  const navigate = useNavigate();

  const handleLogout = async () => {
    const refresh = localStorage.getItem("refresh");

    try {
      await api.post("/auth/logout/", { refresh });
    } catch {
      // token may already be invalid or expired — still clear and redirect
    } finally {
      clearSession();
      navigate("/login", { replace: true });
    }
  };

  return (
    <button className="logout__btn" onClick={handleLogout}>
      Sign out
    </button>
  );
}