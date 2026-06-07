import { useState } from "react";
import AddClientForm from "../components/warehouse/AddClientForm";
import BulkAddClientForm from "../components/warehouse/BulkAddClientForm";
import "../styles/pages/client-page.css";

export default function ClientPage() {
  const [mode, setMode] = useState("single");

  return (
    <div className="client-page">
      <header className="client-page__header">
        <h1 className="client-page__title">Client Management</h1>
        <p className="client-page__subtitle">Single or bulk client workflows</p>
      </header>

      <div className="client-page__tabs" role="tablist" aria-label="Client workflow mode">
        <button
          type="button"
          role="tab"
          aria-selected={mode === "single"}
          className={`client-page__tab${mode === "single" ? " client-page__tab--active" : ""}`}
          onClick={() => setMode("single")}
        >
          Single Client
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={mode === "bulk"}
          className={`client-page__tab${mode === "bulk" ? " client-page__tab--active" : ""}`}
          onClick={() => setMode("bulk")}
        >
          Bulk Clients
        </button>
      </div>

      {mode === "single" && <AddClientForm />}
      {mode === "bulk" && <BulkAddClientForm />}
    </div>
  );
}
