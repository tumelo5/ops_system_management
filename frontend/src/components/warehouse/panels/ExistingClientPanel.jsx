import { useState, useEffect, useCallback } from "react";
import {
  getExistingClients,
  getExistingModels,
  getVersionsByModel,
  validateExistingSelection,
  submitNewVersion,
  submitNewModel,
} from "../../../services/ClientApi";
import Notification, { useNotification } from "../shared/Notifications";
import ScanCard from "../shared/ScanCard";

export default function ExistingClientPanel({ active }) {
  // Dropdown data (fetched from the server; never emptied by a reset)
  const [clientOptions, setClientOptions] = useState([]);
  const [modelOptions, setModelOptions] = useState([]);
  const [versionOptions, setVersionOptions] = useState([]);

  // Selection
  const [client, setClient] = useState("");
  const [modelMode, setModelMode] = useState("existing");
  const [model, setModel] = useState("");
  const [versionMode, setVersionMode] = useState("existing");
  const [version, setVersion] = useState("");
  const [newModelName, setNewModelName] = useState("");
  const [newVersion, setNewVersion] = useState("");
  const [batchCode, setBatchCode] = useState("");

  // Progress
  const [validatedBatchCode, setValidatedBatchCode] = useState(""); // batch the scan will use
  const [batchReady, setBatchReady] = useState(false); // a batch exists for this selection -> scan unlocked
  const [selectionConfirmed, setSelectionConfirmed] = useState(false); // reveals the Linking card (cases 2 & 3)

  const [note, notify, clearNote] = useNotification();

  const loadOptions = useCallback(async () => {
    try {
      const [clients, models] = await Promise.all([getExistingClients(), getExistingModels()]);
      setClientOptions(clients);
      setModelOptions(models);
    } catch (error) {
      notify("error", "Failed to fetch existing data.");
      console.error("Failed to fetch existing data:", error);
    }
  }, [notify]);

  // Refresh whenever the panel becomes the active mode (also covers returning from Correct Info)
  useEffect(() => {
    if (active) loadOptions();
  }, [active, loadOptions]);

  // If the selection changes after a batch was confirmed, the old confirmation no longer applies
  useEffect(() => {
    setBatchReady(false);
    setValidatedBatchCode("");
    setSelectionConfirmed(false);
  }, [client, modelMode, model, versionMode, version, newModelName, newVersion]);

  // Clears the selection only. Dropdown data is kept, then refreshed.
  const resetSelection = () => {
    setClient("");
    setModelMode("existing");
    setModel("");
    setVersionMode("existing");
    setVersion("");
    setNewModelName("");
    setNewVersion("");
    setBatchCode("");
    setValidatedBatchCode("");
    setVersionOptions([]);
    setBatchReady(false);
    setSelectionConfirmed(false);
    clearNote();
  };

  // After Save All the cycle is complete: clear the selection and pick up any new models/versions
  const handleScanSaved = () => {
    resetSelection();
    loadOptions();
  };

  const handleModelChange = async (modelId) => {
    setModel(modelId);
    setVersion("");
    setVersionOptions([]);
    setSelectionConfirmed(false);
    if (!modelId) return;
    try {
      setVersionOptions(await getVersionsByModel(modelId));
    } catch (error) {
      notify("error", "Failed to fetch versions.");
      console.error("Failed to fetch versions:", error);
    }
  };

  // Case 1 — existing client + model + version: validate that a batch exists, then unlock scan
  const handleValidateSelection = async () => {
    clearNote();
    try {
      const response = await validateExistingSelection({ client, model, version });
      setValidatedBatchCode(response.batch_code);
      setBatchReady(true);
      notify("success", response.message);
    } catch (error) {
      notify("error", error.response?.data?.error || "Failed to validate selection.");
      console.error("Validate selection failed:", error);
    }
  };

  // Cases 2 & 3 — new version (existing model) or new model + version, plus a new batch code
  const handleLinkingSubmit = async (e) => {
    e.preventDefault();
    clearNote();
    try {
      const response =
        modelMode === "new"
          ? await submitNewModel({
              client,
              model_name: newModelName,
              version: newVersion,
              batch_code: batchCode,
            })
          : await submitNewVersion({ client, model, version: newVersion, batch_code: batchCode });

      setValidatedBatchCode(batchCode);
      setBatchCode("");
      setBatchReady(true);
      notify("success", response.message || "Batch code created successfully.");
      loadOptions(); // the new model (if any) is now in the list
    } catch (error) {
      notify("error", error.response?.data?.error || error.message || "Failed to create batch code.");
      console.error("Existing linking failed:", error);
    }
  };

  // Case 1: all three existing
  const isCase1 =
    client && modelMode === "existing" && model && versionMode === "existing" && version;

  // Cases 2 & 3: confirm enabled once the new fields are filled
  const canConfirmSelection =
    client &&
    ((modelMode === "existing" && model && versionMode === "new" && newVersion) ||
      (modelMode === "new" && newModelName && newVersion));

  return (
    <div style={active ? undefined : { display: "none" }}>
      <section className="bulk-workflow__section">
        <div className="bulk-workflow__card">
          <h2 className="bulk-workflow__card-title">Existing Client</h2>
          <div className="bulk-workflow__fields">
            <div className="bulk-workflow__field">
              <select
                value={client}
                onChange={(e) => {
                  setClient(e.target.value);
                  setSelectionConfirmed(false);
                }}
              >
                <option value="">Select Client</option>
                {clientOptions.map((c) => (
                  <option key={c.id} value={c.id}>{c.client_name}</option>
                ))}
              </select>
            </div>

            {client && (
              <div className="bulk-workflow__field">
                <select
                  value={modelMode}
                  onChange={(e) => {
                    setModelMode(e.target.value);
                    setModel("");
                    setNewModelName("");
                    setVersionOptions([]);
                    setVersion("");
                    setNewVersion("");
                    setSelectionConfirmed(false);
                  }}
                >
                  <option value="existing">Existing Model</option>
                  <option value="new">New Model</option>
                </select>
              </div>
            )}
          </div>

          {client && modelMode === "existing" && (
            <div className="bulk-workflow__fields" style={{ marginTop: "0.5rem" }}>
              <div className="bulk-workflow__field">
                <select value={model} onChange={(e) => handleModelChange(e.target.value)}>
                  <option value="">Select Model</option>
                  {modelOptions.map((m) => (
                    <option key={m.id} value={m.id}>{m.model_name}</option>
                  ))}
                </select>
              </div>

              {model && (
                <div className="bulk-workflow__field">
                  <select
                    value={versionMode}
                    onChange={(e) => {
                      setVersionMode(e.target.value);
                      setVersion("");
                      setNewVersion("");
                      setSelectionConfirmed(false);
                    }}
                  >
                    <option value="existing">Existing Version</option>
                    <option value="new">New Version</option>
                  </select>
                </div>
              )}

              {model && versionMode === "existing" && (
                <div className="bulk-workflow__field">
                  <select
                    value={version}
                    onChange={(e) => {
                      setVersion(e.target.value);
                      setSelectionConfirmed(false);
                    }}
                  >
                    <option value="">Select Version</option>
                    {versionOptions.map((v) => (
                      <option key={v.id} value={v.id}>{v.version}</option>
                    ))}
                  </select>
                </div>
              )}

              {model && versionMode === "new" && (
                <div className="bulk-workflow__field">
                  <input
                    placeholder="New Version"
                    value={newVersion}
                    onChange={(e) => {
                      setNewVersion(e.target.value);
                      setSelectionConfirmed(false);
                    }}
                  />
                </div>
              )}
            </div>
          )}

          {client && modelMode === "new" && (
            <div className="bulk-workflow__fields" style={{ marginTop: "0.5rem" }}>
              <div className="bulk-workflow__field">
                <input
                  placeholder="New Model Name"
                  value={newModelName}
                  onChange={(e) => {
                    setNewModelName(e.target.value);
                    setSelectionConfirmed(false);
                  }}
                />
              </div>
              <div className="bulk-workflow__field">
                <input
                  placeholder="New Version"
                  value={newVersion}
                  onChange={(e) => {
                    setNewVersion(e.target.value);
                    setSelectionConfirmed(false);
                  }}
                />
              </div>
            </div>
          )}

          {/* Case 1 — validate selection, unlock scan */}
          {isCase1 && !batchReady && (
            <div style={{ marginTop: "0.5rem" }}>
              <div className="bulk-workflow__actions">
                <button
                  type="button"
                  className="bulk-workflow__btn bulk-workflow__btn--primary"
                  onClick={handleValidateSelection}
                >
                  Confirm Selection
                </button>
              </div>
              <Notification state={note} />
            </div>
          )}

          {/* Batch banner — stays until the cycle is finished or the selection changes */}
          {validatedBatchCode && (
            <div
              style={{
                display: "inline-block",
                marginTop: "0.75rem",
                padding: "0.4rem 0.875rem",
                borderRadius: "4px",
                fontSize: "0.8rem",
                fontWeight: 500,
                backgroundColor: "#2563eb",
                color: "#ffffff",
              }}
            >
              ✓ {validatedBatchCode} — ready to scan
            </div>
          )}

          {/* Cases 2 & 3 — confirm to reveal the linking card */}
          {canConfirmSelection && !selectionConfirmed && !batchReady && (
            <div className="bulk-workflow__actions" style={{ marginTop: "0.5rem" }}>
              <button
                type="button"
                className="bulk-workflow__btn bulk-workflow__btn--primary"
                onClick={() => setSelectionConfirmed(true)}
              >
                Confirm Selection
              </button>
            </div>
          )}
        </div>

        {/* Cases 2 & 3 — linking card */}
        {selectionConfirmed && (
          <form className="bulk-workflow__card" onSubmit={handleLinkingSubmit}>
            <h2 className="bulk-workflow__card-subtitle">Linking</h2>
            <div className="bulk-workflow__fields">
              <div className="bulk-workflow__field">
                <input
                  placeholder="New Batch Code"
                  value={batchCode}
                  onChange={(e) => setBatchCode(e.target.value)}
                  disabled={batchReady}
                />
              </div>
            </div>
            <div className="bulk-workflow__actions" style={{ marginTop: "0.5rem" }}>
              <button
                type="submit"
                className="bulk-workflow__btn bulk-workflow__btn--primary"
                disabled={!batchCode || batchReady}
              >
                Create Batch Code
              </button>
            </div>
            <Notification state={note} />
          </form>
        )}
      </section>

      <ScanCard unlocked={batchReady} onSaved={handleScanSaved} />
    </div>
  );
}