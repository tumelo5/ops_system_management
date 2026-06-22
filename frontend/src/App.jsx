import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import BulkAddClientForm from "./components/warehouse/BulkAddClientForm";
import LoginPage from "./pages/LoginPage";
import { getSession } from "./utils/auth";
import "./styles/pages/unauthorized.css";

function LoginRoute() {
  const { isAuthenticated, dashboardPath } = getSession();

  if (isAuthenticated && dashboardPath) {
    return <Navigate to={dashboardPath} replace />;
  }

  return <LoginPage />;
}

function PrivateRoute({ children, department }) {
  const { isAuthenticated, department: userDepartment } = getSession();

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  if (department && userDepartment !== department) {
    return <Navigate to="/unauthorized" replace />;
  }

  return children;
}

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Navigate to="/login" replace />} />

        <Route path="/login" element={<LoginRoute />} />

        <Route
          path="/warehouse/*"
          element={
            <PrivateRoute department="warehouse">
              <BulkAddClientForm />
            </PrivateRoute>
          }
        />

        <Route
          path="/unauthorized"
          element={
            <div className="unauthorized-page">
              <h2 className="unauthorized-page__message">🚫 Access Denied</h2>
            </div>
          }
        />

        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
