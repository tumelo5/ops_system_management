import { useState } from "react";
import "../../styles/components/bulk-workflow.css";
import Navbar from "../navbar/navbar";
import ModePicker from "./ModePicker";
import CompanySetUp from "./CompanySetUp";
import BulkClientsPanel from "./panels/BulkClientsPanel";
import ExistingClientPanel from "./panels/ExistingClientPanel";
import RentalPanel from "./panels/RentalPanel";
import EndRentalPanel from "./panels/EndRentalPanel";
import CorrectionPanel from "./panels/CorrectionPanel";

export default function WarehousePage() {
  const [mode, setMode] = useState("");
  const [returnMode, setReturnMode] = useState("bulk_clients"); // where Correct Info returns to
  const [intakeVersion, setIntakeVersion] = useState(0); // bumped when intake data changes, refreshes CompanySetUp

  // Switching modes no longer resets anything. The two intake panels stay mounted
  // (hidden when inactive), so in-progress work is still there when the user returns,
  // and each panel refetches its server data whenever it becomes active.
  const handleModeChange = (value) => {
    // Correct Info is a side trip: remember which intake mode to come back to
    if (value === "correct_info" && mode !== "correct_info") {
      setReturnMode(mode === "existing_client" ? "existing_client" : "bulk_clients");
    }
    setMode(value);
  };

  const isIntakeMode = mode === "bulk_clients" || mode === "existing_client";

  return (
    <div className="bulk-workflow">
      {/* Navbar sits above, aligned right */}
      <div style={{ display: "flex", justifyContent: "flex-end" }}>
        <Navbar />
      </div>

      {/* Header */}
      <header
        className={`bulk-workflow__header${mode ? " bulk-workflow__header--compact" : ""}`}
        style={{ textAlign: "center", justifyContent: "center", flexDirection: "column", alignItems: "center" }}
      >
        <h1 className="bulk-workflow__title">Warehouse</h1>
        <div className={`bulk-workflow__intro${mode ? " bulk-workflow__intro--hidden" : ""}`}>
          <div>
            <p className="bulk-workflow__subtitle">
              Add clients | Link batch codes | Scan devices | Manage rentals | Returning devices
            </p>
            <p className="bulk-workflow__tagline">One system. Every device. Every department.</p>
          </div>
        </div>
      </header>

      {/* Mode picker */}
      <ModePicker value={mode} onChange={handleModeChange} />

      {/* One-time company setup — shown only in the client-intake modes */}
      {isIntakeMode && <CompanySetUp refreshKey={`${mode}-${intakeVersion}`} />}

      {/* Panels that are fine to mount only while active */}
      {mode === "assign_rental" && <RentalPanel />}
      {mode === "end_rental" && <EndRentalPanel />}
      {mode === "correct_info" && <CorrectionPanel onBack={() => setMode(returnMode)} />}

      {/* Intake panels: always mounted so progress survives switching modes */}
      <BulkClientsPanel
        active={mode === "bulk_clients"}
        onDataChanged={() => setIntakeVersion((v) => v + 1)}
      />
      <ExistingClientPanel active={mode === "existing_client"} />
    </div>
  );
}