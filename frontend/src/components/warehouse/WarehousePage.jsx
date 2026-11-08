import { useState } from "react";
import "../../styles/components/bulk-workflow.css";

import Navbar from "../navbar/navbar";
import ModePicker from "./ModePicker";
import CompanySetUp from "./CompanySetUp";
import TransitionPanel from "./panels/TransitionPanel";

import BulkClientsPanel from "./panels/BulkClientsPanel";
import ExistingClientPanel from "./panels/ExistingClientPanel";
import RentalPanel from "./panels/RentalPanel";
import EndRentalPanel from "./panels/EndRentalPanel";
import CorrectionPanel from "./panels/CorrectionPanel";

export default function WarehousePage() {
  const [mode, setMode] = useState("");
  const [returnMode, setReturnMode] = useState("bulk_clients");
  const [intakeVersion, setIntakeVersion] = useState(0);

  const handleModeChange = (value) => {
    if (value === "correct_info" && mode !== "correct_info") {
      setReturnMode(
        mode === "existing_client" ? "existing_client" : "bulk_clients"
      );
    }

    setMode(value);
  };

  const isIntakeMode =
    mode === "bulk_clients" || mode === "existing_client";

  return (
    <div classname="warehouse-page">
      <div className="bulk-workflow">
        <div style={{ display: "flex", justifyContent: "flex-end" }}>
          <Navbar />
        </div>
    

      <header
        className={`bulk-workflow__header${
          mode ? " bulk-workflow__header--compact" : ""
        }`}
        style={{
          textAlign: "center",
          justifyContent: "center",
          flexDirection: "column",
          alignItems: "center",
        }}
      >
        <h1 className="bulk-workflow__title">Warehouse</h1>

        <div
          className={`bulk-workflow__intro${
            mode ? " bulk-workflow__intro--hidden" : ""
          }`}
        >
          <div>
            <p className="bulk-workflow__subtitle">
              Add clients | Link batch codes | Scan devices | Manage rentals |
              Returning devices
            </p>

            <p className="bulk-workflow__tagline">
              One system. Every device. Every department.
            </p>
          </div>
        </div>
      </header>

      <ModePicker value={mode} onChange={handleModeChange} />

      {/* Shared company setup for both intake modes */}
      <TransitionPanel active={isIntakeMode}>
        <CompanySetUp refreshKey={intakeVersion} />
      </TransitionPanel>

      {/* Client and batch workflows */}
      <TransitionPanel active={mode === "bulk_clients"}>
        <BulkClientsPanel
          active={mode === "bulk_clients"}
          onDataChanged={() => setIntakeVersion((v) => v + 1)}
        />
      </TransitionPanel>

      <TransitionPanel active={mode === "existing_client"}>
        <ExistingClientPanel active={mode === "existing_client"} />
      </TransitionPanel>

      {/* Rental workflows */}
      <TransitionPanel active={mode === "assign_rental"}>
        <RentalPanel />
      </TransitionPanel>

      <TransitionPanel active={mode === "end_rental"}>
        <EndRentalPanel />
      </TransitionPanel>

      {/* Correction workflow */}
      <TransitionPanel active={mode === "correct_info"}>
        <CorrectionPanel onBack={() => setMode(returnMode)} />
      </TransitionPanel>
    </div>
  </div>
  );
}