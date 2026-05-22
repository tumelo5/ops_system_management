import { useState } from "react";
import AddClientForm from "../components/client/AddClientForm";
import BulkAddClientForm from "../components/client/BulkAddClientForm";

export default function ClientPage() {
  const [mode, setMode] = useState("single");

  return (
    <div>
      <h1>Client Management</h1>

      <button onClick={() => setMode("single")}>
        Single Client
      </button>

      <button onClick={() => setMode("bulk")}>
        Bulk Clients
      </button>

      {mode === "single" && <AddClientForm />}
      {mode === "bulk" && <BulkAddClientForm />}
    </div>
  );
}