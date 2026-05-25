import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import AddClientForm from "./components/warehouse/AddClientForm";
import HRPage from "./pages/HRPage";
import Login from "./pages/LoginPage";

function isAuthenticated() {
  return !!localStorage.getItem("access");
}

function PrivateRoute({ children, department }) {
  if (!isAuthenticated()) return <Navigate to="/login" replace />;
  if (department && localStorage.getItem("department") !== department) {
    return <Navigate to="/unauthorized" replace />;
  }
  return children;
}

function App() {
  return (
    <BrowserRouter>
      <Routes>

        {/* Default → login */}
        <Route path="/" element={<Navigate to="/login" replace />} />

        {/* Login page */}
        <Route path="/login" element={
          isAuthenticated()
            ? <Navigate to={`/${localStorage.getItem("department")}`} replace />
            : <Login />
        } />

        {/* HR */}
        <Route path="/hr/*" element={
          <PrivateRoute department="hr">
            <HRPage />
          </PrivateRoute>
        } />

        {/* Warehouse */}
        <Route path="/warehouse/*" element={
          <PrivateRoute department="warehouse">
            <AddClientForm />
          </PrivateRoute>
        } />

        {/* Access denied */}
        <Route path="/unauthorized" element={
          <h2 style={{ textAlign: "center", marginTop: "4rem" }}>🚫 Access Denied</h2>
        } />

        {/* Catch-all → login */}
        <Route path="*" element={<Navigate to="/login" replace />} />

      </Routes>
    </BrowserRouter>
  );
}

export default App;