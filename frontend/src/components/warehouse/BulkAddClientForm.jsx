import { useState, useEffect } from "react";
import { submitDeviceWorkflow, getExistingClients, getExistingModels, getVersionsByModel, submitClientWorkflow } from "../../services/ClientApi";
import "../../styles/components/bulk-workflow.css";
import "../navbar/logout"
import Logout from "../navbar/logout";
import Navbar from "../navbar/navbar";


export default function BulkAddClientForm() {
  const [mode, setMode] = useState("");

  // Section-specific notification states
  const [bulkBaseNotification, setBulkBaseNotification] = useState(null);
  const [bulkLinkingNotification, setBulkLinkingNotification] = useState(null);
  const [existingNotification, setExistingNotification] = useState(null);
  const [scanNotification, setScanNotification] = useState(null);

  // Gates
  const [bulkBaseCreated, setBulkBaseCreated] = useState(false);
  const [bulkLinkingCreated, setBulkLinkingCreated] = useState(false);

  // Add Clients — Base rows (2 by default)
  const [bulkBase, setBulkBase] = useState([
    { client_name: "", model_name: "" },
    { client_name: "", model_name: "" },
  ]);

  // Add Clients — Linking rows (mirrors base)
  const [bulkLinking, setBulkLinking] = useState([
    { batch_code: "", client: "", version: "", model: "" },
    { batch_code: "", client: "", version: "", model: "" },
  ]);

  // Dropdown data
  const [clientOptions, setClientOptions] = useState([]);
  const [modelOptions, setModelOptions] = useState([]);

  // Scan
  const [serialNumber, setSerialNumber] = useState("");
  const [scannedDevices, setScannedDevices] = useState([]);
  const [scanReady, setScanReady] = useState(false);

  // Existing client state
  const [modelOptions2, setModelOptions2] = useState([]);
  const [versionOptions, setVersionOptions] = useState([]);
  const [existingClient, setExistingClient] = useState("");
  const [existingModel, setExistingModel] = useState("");
  const [existingVersion, setExistingVersion] = useState("");
  const [existingBatchCode, setExistingBatchCode] = useState("");
  const [existingLinkingCreated, setExistingLinkingCreated] = useState(false);
  const [existingSelectionConfirmed, setExistingSelectionConfirmed] = useState(false);
  const [validatedBatchCode, setValidatedBatchCode] = useState("");

  const [modelMode, setModelMode] = useState("existing");
  const [versionMode, setVersionMode] = useState("existing");
  const [newModelName, setNewModelName] = useState("");
  const [newVersion, setNewVersion] = useState("");

  const notify = (setter, type, message) => {
    setter({ type, message });
    setTimeout(() => setter(null), 5000);
  };

  useEffect(() => {
    if (mode !== "existing_client") return;
    const fetchData = async () => {
      try {
        const [clients, models] = await Promise.all([getExistingClients(), getExistingModels()]);
        setClientOptions(clients);
        setModelOptions2(models);
      } catch (error) {
        notify(setExistingNotification, "error", "Failed to fetch existing data.");
        console.error("Failed to fetch existing data:", error);
      }
    };
    fetchData();
  }, [mode]);

  // Base row handlers
  const handleBulkBaseChange = (index, field, value) => {
    const updated = [...bulkBase];
    updated[index][field] = value;
    setBulkBase(updated);
  };

  const MAX_ROWS = 5;

  const handleAddRow = () => {
    if (bulkBase.length >= MAX_ROWS) return;
    setBulkBase(prev => [...prev, { client_name: "", model_name: "" }]);
    setBulkLinking(prev => [...prev, { batch_code: "", client: "", version: "", model: "" }]);
  };

  const handleRemoveBulkBaseRow = (index) => {
    if (bulkBase.length === 1) return;
    setBulkBase(prev => prev.filter((_, i) => i !== index));
    setBulkLinking(prev => prev.filter((_, i) => i !== index));
  };

  const handleBulkBaseSubmit = async (e) => {
    e.preventDefault();
    setBulkBaseNotification(null);
    try {
      const response = await submitClientWorkflow({ type: "bulk_clients", step: "base", clients: bulkBase });
      setClientOptions(response.clients || []);
      setModelOptions(response.models || []);
      setBulkBaseCreated(true);
      setBulkLinking(bulkBase.map(() => ({ batch_code: "", client: "", version: "", model: "" })));
      notify(setBulkBaseNotification, "success", response.message || "Clients and models created.");
      console.log(response);
    } catch (error) {
      const message = error.response?.data?.error || "Failed to create clients and models.";
      notify(setBulkBaseNotification, "error", message);
      console.error("Bulk base submission failed:", error);
    }
  };

  // Linking row handlers
  const handleBulkLinkingChange = (index, field, value) => {
    const updated = [...bulkLinking];
    updated[index][field] = value;
    setBulkLinking(updated);
  };

  const handleBulkLinkingSubmit = async (e) => {
    e.preventDefault();
    setBulkLinkingNotification(null);
    try {
      const response = await submitClientWorkflow({ type: "bulk_clients", step: "linking", links: bulkLinking });
      setBulkLinking(bulkBase.map(() => ({ batch_code: "", client: "", version: "", model: "" })));
      setBulkBaseCreated(false);
      setBulkLinkingCreated(true);
      notify(setBulkLinkingNotification, "success", response.message || "Batch codes and versions created.");
      console.log(response);
    } catch (error) {
      const data = error.response?.data;
    
      // Field priority order — matches the form layout top-left → bottom-right
      const fieldOrder = ['batch_code', 'client', 'version', 'model'];
    
      if (data && typeof data === 'object') {
        // Find the first error in field order
        const firstField = fieldOrder.find(f => data[f]);
        const message = firstField
          ? (Array.isArray(data[firstField]) ? data[firstField][0] : data[firstField])
          : data?.error || "Failed to create batch codes and versions.";
        notify(setBulkLinkingNotification, "error", message);
      } else {
        notify(setBulkLinkingNotification, "error", data?.error || "Failed to create batch codes and versions.");
      }
    
      console.error("Bulk linking submission failed:", error);
    }
  };

  // Existing client handlers
  const handleExistingModelChange = async (modelId) => {
    setExistingModel(modelId);
    setExistingVersion("");
    setVersionOptions([]);
    setExistingSelectionConfirmed(false);
    if (!modelId) return;
    try {
      const versions = await getVersionsByModel(modelId);
      setVersionOptions(versions);
    } catch (error) {
      notify(setExistingNotification, "error", "Failed to fetch versions.");
      console.error("Failed to fetch versions:", error);
    }
  };

  // Case 1 — validate that a batch exists for the selection, then unlock scan
  const handleValidateSelection = async () => {
    setExistingNotification(null);
    try {
      const response = await submitClientWorkflow({
        type: "existing_client",
        step: "validate_selection",
        client: existingClient,
        model: existingModel,
        version: existingVersion,
      });
      setValidatedBatchCode(response.batch_code);
      setExistingLinkingCreated(true);
      notify(setExistingNotification, "success", response.message);
      console.log(response);
    } catch (error) {
      const message = error.response?.data?.error || "Failed to validate selection.";
      notify(setExistingNotification, "error", message);
      console.error("Validate selection failed:", error);
    }
  };

  // Case 2 & 3 — create new version/model and batch code
  const handleExistingLinkingSubmit = async (e) => {
    e.preventDefault();
    setExistingNotification(null);

    const isNewModel = modelMode === "new";

    try {
      let response;

      if (isNewModel) {
        // Case 3: new model + new version + new batch code
        response = await submitClientWorkflow({
          type: "existing_client",
          step: "new_model",
          client: existingClient,
          model_name: newModelName,
          version: newVersion,
          batch_code: existingBatchCode,
        });
      } else {
        // Case 2: existing model + new version + new batch code
        response = await submitClientWorkflow({
          type: "existing_client",
          step: "new_version",
          client: existingClient,
          model: existingModel,
          version: newVersion,
          batch_code: existingBatchCode,
        });
      }

      notify(setExistingNotification, "success", response.message || "Batch code created successfully.");
      console.log(response);
      setExistingBatchCode("");
      setExistingLinkingCreated(true);

    } catch (error) {
      const message = error.response?.data?.error || error.message || "Failed to create batch code.";
      notify(setExistingNotification, "error", message);
      console.error("Existing linking failed:", error);
    }
  };

  // Scan handlers
  const handleSerialKeyDown = async (e) => {
    if (e.key !== "Enter") return;
    e.preventDefault();
    if (!serialNumber.trim()) return;
    if (scannedDevices.some(d => d.serial_number === serialNumber.trim())) {
      notify(setScanNotification, "error", `${serialNumber.trim()} already scanned.`);
      return;
    }
    setScanNotification(null);
    try {
      const response = await submitDeviceWorkflow({ type: "scan", serial_number: serialNumber });
      setScannedDevices(prev => [...prev, response.device]);
      setSerialNumber("");
      console.log(response);
    } catch (error) {
      const message = error.response?.data?.error || "Failed to scan device.";
      notify(setScanNotification, "error", message);
      console.error("Scan failed:", error.response?.data);
    }
  };

  const handleRemove = (serial_number) => {
    setScannedDevices(prev => prev.filter(d => d.serial_number !== serial_number));
  };

  const handleSaveAll = async () => {
    if (scannedDevices.length === 0) return;
    setScanNotification(null);
    try {
      const response = await submitDeviceWorkflow({
        type: "confirm_bulk",
        serial_numbers: scannedDevices.map(d => d.serial_number)
      });
      setScannedDevices([]);
      setSerialNumber("");
      resetExistingClient();
      notify(setScanNotification, "success", response.message || "All devices saved and activated.");
      console.log(response);
    } catch (error) {
      const message = error.response?.data?.error || "Failed to save devices.";
      notify(setScanNotification, "error", message);
      console.error("Save all failed:", error);
    }
  };

  const scanUnlocked = bulkLinkingCreated || scanReady || existingLinkingCreated;

  const resetExistingClient = () => {
    setExistingClient("");
    setExistingModel("");
    setExistingVersion("");
    setExistingBatchCode("");
    setValidatedBatchCode("");
    setModelOptions2([]);
    setVersionOptions([]);
    setModelMode("existing");
    setVersionMode("existing");
    setNewModelName("");
    setNewVersion("");
    setExistingLinkingCreated(false);
    setExistingSelectionConfirmed(false);
    setExistingNotification(null);
  };

  // Case 1: existing client + existing model + existing version — validate only
  const isCase1 =
    existingClient &&
    modelMode === "existing" &&
    existingModel &&
    versionMode === "existing" &&
    existingVersion;

  // Case 2 & 3: confirm button enabled when new version or new model fields are filled
  const canConfirmSelection =
    existingClient && (
      (modelMode === "existing" && existingModel && versionMode === "new" && newVersion) ||
      (modelMode === "new" && newModelName && newVersion)
    );

  const Notification = ({ state }) => {
    if (!state) return null;
    return (
      <div style={{
        display: "inline-block",
        marginTop: "0.5rem",
        padding: "0.4rem 0.875rem",
        borderRadius: "4px",
        fontSize: "0.8rem",
        fontWeight: 500,
        backgroundColor: state.type === "success" ? "#16a34a" : "#dc2626",
        color: "#ffffff",
      }}>
        {state.message}
      </div>
    );
  };

  const rowLabel = (i) => `#${i + 1}`;

  return (
    <div className="bulk-workflow">

      {/* Navbar sits above, aligned right */}
      <div style={{ display: "flex", justifyContent: "flex-end" }}>
        <Navbar />
      </div>

      {/* Header */}
      <header className="bulk-workflow__header" style={{ textAlign: "center", justifyContent: "center", flexDirection: "column", alignItems: "center" }}>
        <h1 className="bulk-workflow__title">Client Workflow</h1>
        <p className="bulk-workflow__subtitle">Add clients, link batch codes, and scan devices</p>
      </header>

      {/* Mode selector */}
      <div style={{ display: "flex", justifyContent: "center", margin: "1rem 0" }}>
        <select
          className="bulk-workflow__mode-select"
          style={{ width: "auto", minWidth: "180px" }}
          value={mode}
          onChange={(e) => {
            setMode(e.target.value);
            setBulkBaseCreated(false);
            setBulkLinkingCreated(false);
            setScannedDevices([]);
            setSerialNumber("");
            setClientOptions([]);
            setModelOptions([]);
            setScanReady(false);
            setBulkBaseNotification(null);
            setBulkLinkingNotification(null);
            setScanNotification(null);
            resetExistingClient();
          }}
        >
          <option value="">— Select Mode —</option>
          <option value="bulk_clients">Add Clients</option>
          <option value="existing_client">Existing Client</option>
        </select>
      </div>

      {/* Add Clients Mode */}
      {mode === "bulk_clients" && (
        <section className="bulk-workflow__section">

          {/* Base card */}
          <form className="bulk-workflow__card" onSubmit={handleBulkBaseSubmit}>
            <h2 className="bulk-workflow__card-title">Add Clients</h2>

            {bulkBase.map((entry, index) => (
              <div key={index} className="bulk-workflow__entry" style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "0.5rem" }}>
                <span style={{ fontSize: "0.75rem", color: "#6b7280", minWidth: "1.5rem", textAlign: "right" }}>
                  {rowLabel(index)}
                </span>
                <div className="bulk-workflow__fields" style={{ flex: 1, margin: 0 }}>
                  <div className="bulk-workflow__field">
                    <input
                      placeholder="Client Name"
                      value={entry.client_name}
                      onChange={(e) => handleBulkBaseChange(index, "client_name", e.target.value)}
                      disabled={bulkBaseCreated}
                    />
                  </div>
                  <div className="bulk-workflow__field">
                    <input
                      placeholder="Model Name"
                      value={entry.model_name}
                      onChange={(e) => handleBulkBaseChange(index, "model_name", e.target.value)}
                      disabled={bulkBaseCreated}
                    />
                  </div>
                </div>
                {!bulkBaseCreated && bulkBase.length > 1 && (
                  <button
                    type="button"
                    className="bulk-workflow__btn-remove"
                    onClick={() => handleRemoveBulkBaseRow(index)}
                    title="Remove row"
                    style={{ flexShrink: 0 }}
                  >
                    🗑
                  </button>
                )}
              </div>
            ))}

            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: "0.5rem" }}>
              <div>
                {!bulkBaseCreated && (
                  <button
                    type="button"
                    className="bulk-workflow__btn bulk-workflow__btn--secondary"
                    onClick={handleAddRow}
                    disabled={bulkBase.length >= MAX_ROWS}
                    title={bulkBase.length >= MAX_ROWS ? "Maximum of 5 rows reached" : ""}
                  >
                    + Add Row {bulkBase.length >= MAX_ROWS ? "(max)" : `(${bulkBase.length}/5)`}
                  </button>
                )}
              </div>
              <button type="submit" className="bulk-workflow__btn bulk-workflow__btn--primary" disabled={bulkBaseCreated}>
                Save Clients
              </button>
            </div>
            <Notification state={bulkBaseNotification} />
          </form>

          {/* Linking card */}
          <form className="bulk-workflow__card" onSubmit={handleBulkLinkingSubmit}>
            <h2 className="bulk-workflow__card-subtitle">Linking</h2>

            {bulkLinking.map((entry, index) => (
              <div key={index} className="bulk-workflow__entry" style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "0.5rem" }}>
                <span style={{ fontSize: "0.75rem", color: "#6b7280", minWidth: "1.5rem", textAlign: "right" }}>
                  {rowLabel(index)}
                </span>
                <div style={{ flex: 1 }}>
                  <div className="bulk-workflow__fields" style={{ margin: 0, marginBottom: "0.5rem" }}>
                    <div className="bulk-workflow__field">
                      <input placeholder="Batch Code" value={entry.batch_code} onChange={(e) => handleBulkLinkingChange(index, "batch_code", e.target.value)} disabled={!bulkBaseCreated} />
                    </div>
                    <div className="bulk-workflow__field">
                      <select value={entry.client} onChange={(e) => handleBulkLinkingChange(index, "client", e.target.value)} disabled={!bulkBaseCreated}>
                        <option value="">Client</option>
                        {clientOptions.map((c) => (
                          <option key={c.id} value={c.id}>{c.client_name}</option>
                        ))}
                      </select>
                    </div>
                  </div>
                  <div className="bulk-workflow__fields" style={{ margin: 0 }}>
                    <div className="bulk-workflow__field">
                      <input placeholder="Version" value={entry.version} onChange={(e) => handleBulkLinkingChange(index, "version", e.target.value)} disabled={!bulkBaseCreated} />
                    </div>
                    <div className="bulk-workflow__field">
                      <select value={entry.model} onChange={(e) => handleBulkLinkingChange(index, "model", e.target.value)} disabled={!bulkBaseCreated}>
                        <option value="">Model</option>
                        {modelOptions.map((m) => (
                          <option key={m.id} value={m.id}>{m.model_name}</option>
                        ))}
                      </select>
                    </div>
                  </div>
                </div>
              </div>
            ))}

            <div style={{ display: "flex", justifyContent: "flex-end", marginTop: "0.5rem" }}>
              <button type="submit" className="bulk-workflow__btn bulk-workflow__btn--primary" disabled={!bulkBaseCreated}>
                Save Links
              </button>
            </div>
            <Notification state={bulkLinkingNotification} />
          </form>
        </section>
      )}

      {/* Existing Client Mode */}
      {mode === "existing_client" && (
        <section className="bulk-workflow__section">
          <div className="bulk-workflow__card">
            <h2 className="bulk-workflow__card-title">Existing Client</h2>
            <div className="bulk-workflow__fields">
              <div className="bulk-workflow__field">
                <select value={existingClient} onChange={(e) => { setExistingClient(e.target.value); setExistingSelectionConfirmed(false); }}>
                  <option value="">Select Client</option>
                  {clientOptions.map((c) => (
                    <option key={c.id} value={c.id}>{c.client_name}</option>
                  ))}
                </select>
              </div>

              {existingClient && (
                <div className="bulk-workflow__field">
                  <select value={modelMode} onChange={(e) => {
                    setModelMode(e.target.value);
                    setExistingModel("");
                    setNewModelName("");
                    setVersionOptions([]);
                    setExistingVersion("");
                    setNewVersion("");
                    setExistingSelectionConfirmed(false);
                  }}>
                    <option value="existing">Existing Model</option>
                    <option value="new">New Model</option>
                  </select>
                </div>
              )}
            </div>

            {existingClient && modelMode === "existing" && (
              <div className="bulk-workflow__fields" style={{ marginTop: "0.5rem" }}>
                <div className="bulk-workflow__field">
                  <select value={existingModel} onChange={(e) => handleExistingModelChange(e.target.value)}>
                    <option value="">Select Model</option>
                    {modelOptions2.map((m) => (
                      <option key={m.id} value={m.id}>{m.model_name}</option>
                    ))}
                  </select>
                </div>

                {existingModel && (
                  <div className="bulk-workflow__field">
                    <select value={versionMode} onChange={(e) => {
                      setVersionMode(e.target.value);
                      setExistingVersion("");
                      setNewVersion("");
                      setExistingSelectionConfirmed(false);
                    }}>
                      <option value="existing">Existing Version</option>
                      <option value="new">New Version</option>
                    </select>
                  </div>
                )}

                {existingModel && versionMode === "existing" && (
                  <div className="bulk-workflow__field">
                    <select value={existingVersion} onChange={(e) => { setExistingVersion(e.target.value); setExistingSelectionConfirmed(false); }}>
                      <option value="">Select Version</option>
                      {versionOptions.map((v) => (
                        <option key={v.id} value={v.id}>{v.version}</option>
                      ))}
                    </select>
                  </div>
                )}

                {existingModel && versionMode === "new" && (
                  <div className="bulk-workflow__field">
                    <input placeholder="New Version" value={newVersion} onChange={(e) => { setNewVersion(e.target.value); setExistingSelectionConfirmed(false); }} />
                  </div>
                )}
              </div>
            )}

            {existingClient && modelMode === "new" && (
              <div className="bulk-workflow__fields" style={{ marginTop: "0.5rem" }}>
                <div className="bulk-workflow__field">
                  <input placeholder="New Model Name" value={newModelName} onChange={(e) => { setNewModelName(e.target.value); setExistingSelectionConfirmed(false); }} />
                </div>
                <div className="bulk-workflow__field">
                  <input placeholder="New Version" value={newVersion} onChange={(e) => { setNewVersion(e.target.value); setExistingSelectionConfirmed(false); }} />
                </div>
              </div>
            )}

            {/* Case 1 — validate selection, unlock scan */}
            {isCase1 && !existingLinkingCreated && (
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
                <Notification state={existingNotification} />
              </div>
            )}

            {/* Case 1 — persistent compact batch code banner, cleared after Save All */}
            {validatedBatchCode && (
              <div style={{
                display: "inline-block",
                marginTop: "0.75rem",
                padding: "0.4rem 0.875rem",
                borderRadius: "4px",
                fontSize: "0.8rem",
                fontWeight: 500,
                backgroundColor: "#2563eb",
                color: "#ffffff",
              }}>
                ✓ {validatedBatchCode} — ready to scan
              </div>
            )}

            {/* Case 2 & 3 — confirm to reveal linking card */}
            {canConfirmSelection && !existingSelectionConfirmed && (
              <div className="bulk-workflow__actions" style={{ marginTop: "0.5rem" }}>
                <button
                  type="button"
                  className="bulk-workflow__btn bulk-workflow__btn--primary"
                  onClick={() => setExistingSelectionConfirmed(true)}
                >
                  Confirm Selection
                </button>
              </div>
            )}
          </div>

          {/* Case 2 & 3 — linking card */}
          {existingSelectionConfirmed && (
            <form className="bulk-workflow__card" onSubmit={handleExistingLinkingSubmit}>
              <h2 className="bulk-workflow__card-subtitle">Linking</h2>
              <div className="bulk-workflow__fields">
                <div className="bulk-workflow__field">
                  <input
                    placeholder="New Batch Code"
                    value={existingBatchCode}
                    onChange={(e) => setExistingBatchCode(e.target.value)}
                    disabled={existingLinkingCreated}
                  />
                </div>
              </div>
              <div className="bulk-workflow__actions" style={{ marginTop: "0.5rem" }}>
                <button
                  type="submit"
                  className="bulk-workflow__btn bulk-workflow__btn--primary"
                  disabled={!existingBatchCode || existingLinkingCreated}
                >
                  Create Batch Code
                </button>
              </div>
              <Notification state={existingNotification} />
            </form>
          )}
        </section>
      )}

      {/* Scan Device */}
      {mode && (
        <section className="bulk-workflow__scan">
          <div className="bulk-workflow__card">
            <h2 className="bulk-workflow__card-title">Scan Device</h2>

            <div className="bulk-workflow__field">
              <input
                placeholder="Serial number — press Enter to add"
                value={serialNumber}
                onChange={(e) => setSerialNumber(e.target.value)}
                onKeyDown={handleSerialKeyDown}
                disabled={!scanUnlocked}
              />
            </div>

            <Notification state={scanNotification} />

            {scannedDevices.length > 0 && (
              <div className="bulk-workflow__device-details">
                <table className="bulk-workflow__device-table">
                  <thead>
                    <tr>
                      <th>Serial No.</th>
                      <th>Client</th>
                      <th>Batch</th>
                      <th>Model</th>
                      <th>Version</th>
                      <th>Status</th>
                      <th></th>
                    </tr>
                  </thead>
                  <tbody>
                    {scannedDevices.map((device) => (
                      <tr key={device.serial_number}>
                        <td>{device.serial_number}</td>
                        <td>{device.client_name}</td>
                        <td>{device.batch_code}</td>
                        <td>{device.model_name}</td>
                        <td>{device.version_name}</td>
                        <td>{device.status}</td>
                        <td>
                          <button
                            type="button"
                            className="bulk-workflow__btn-remove"
                            onClick={() => handleRemove(device.serial_number)}
                            title="Remove"
                          >
                            🗑
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>

                <div style={{ display: "flex", justifyContent: "flex-end", marginTop: "0.5rem" }}>
                  <button type="button" className="bulk-workflow__btn bulk-workflow__btn--primary" onClick={handleSaveAll}>
                    Save All ({scannedDevices.length})
                  </button>
                </div>
              </div>
            )}
          </div>
        </section>
      )}
    </div>
  );
}

/*
  handleExistingLinkingSubmit — completely rewritten

  Removed the old model_only branch entirely
  Case 3 (isNewModel) now sends step: "new_model" with client, model_name, version, batch_code
  Case 2 (!isNewModel) now sends step: "new_version" with client, model, version, batch_code
  Both paths set existingLinkingCreated(true) on success, which unlocks the scan section

  canConfirmSelection — tightened

  Existing model path now only allows versionMode === "new" to satisfy the condition — selecting an existing version no longer enables the Confirm button

  isCase1 — new derived boolean

  Detects when the user has selected existing client + existing model + existing version
  Renders an amber warning banner instead of the Confirm button: "Same model and version already exists — this case will be supported in a future update."
  Honest UX rather than a broken or silent dead end
*/