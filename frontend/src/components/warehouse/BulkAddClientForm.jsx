import { useState, useEffect } from "react";
import { submitBulkWorkflow, submitDeviceWorkflow, getExistingClients, getExistingModels, getVersionsByModel, submitScanWorkflow } from "../../services/ClientApi";
import "../../styles/components/bulk-workflow.css";


export default function BulkAddClientForm() {
  const [mode, setMode] = useState("");

  // Notification state
  const [notification, setNotification] = useState(null);

  // Single client gates
  const [baseCreated, setBaseCreated] = useState(false);
  const [linkingCreated, setLinkingCreated] = useState(false);

  // Bulk clients gate
  const [bulkBaseCreated, setBulkBaseCreated] = useState(false);
  const [bulkLinkingCreated, setBulkLinkingCreated] = useState(false);

  // Single client — Client
  const [clientName, setClientName] = useState("");
  const [clientStatus, setClientStatus] = useState("");

  // Single client — Model
  const [modelName, setModelName] = useState("");
  const [modelStatus, setModelStatus] = useState("");

  // Single client — Batch code
  const [batchcode, setBatchCode] = useState("");
  const [client, setClient] = useState("");

  // Single client — Version
  const [version, setVersion] = useState("");
  const [model, setModel] = useState("");

  // Bulk clients — Base
  const [bulkBase, setBulkBase] = useState([
    { client_name: "", client_status: "", model_name: "", model_status: "" },
    { client_name: "", client_status: "", model_name: "", model_status: "" },
    { client_name: "", client_status: "", model_name: "", model_status: "" },
  ]);

  // Bulk clients — Linking
  const [bulkLinking, setBulkLinking] = useState([
    { batch_code: "", client: "", version: "", model: "" },
    { batch_code: "", client: "", version: "", model: "" },
    { batch_code: "", client: "", version: "", model: "" },
  ]);

  // Dropdown data (shared between single and bulk)
  const [clientOptions, setClientOptions] = useState([]);
  const [modelOptions, setModelOptions] = useState([]);

  // Device capture — array of scanned devices
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

  // Existing client — model and version mode toggles
  const [modelMode, setModelMode] = useState("existing"); // "existing" | "new"
  const [versionMode, setVersionMode] = useState("existing"); // "existing" | "new"

  // New model fields (when modelMode === "new")
  const [newModelName, setNewModelName] = useState("");
  const [newModelStatus, setNewModelStatus] = useState("");
  const [newVersion, setNewVersion] = useState("");

  // Helper — show notification and auto-clear after 5 seconds
  const notify = (type, message) => {
    setNotification({ type, message });
    setTimeout(() => setNotification(null), 5000);
  };

  // Fetch existing clients and models when existing_client mode is selected
  useEffect(() => {
    if (mode !== "existing_client") return;

    const fetchData = async () => {
      try {
        const [clients, models] = await Promise.all([
          getExistingClients(),
          getExistingModels()
        ]);
        setClientOptions(clients);
        setModelOptions2(models);
      } catch (error) {
        notify("error", "Failed to fetch existing data.");
        console.error("Failed to fetch existing data:", error);
      }
    };
    fetchData();
  }, [mode]);

  // Single client handlers
  const handleBaseSubmit = async (e) => {
    e.preventDefault();
    setNotification(null);
    try {
      const response = await submitBulkWorkflow({
        type: "single_client",
        step: "base",
        client_name: clientName,
        client_status: clientStatus,
        model_name: modelName,
        model_status: modelStatus
      });

      setClientOptions(response.clients || []);
      setModelOptions(response.models  || []);

      setClientName("");
      setClientStatus("");
      setModelName("");
      setModelStatus("");
      setBaseCreated(true);

      notify("success", response.message || "Client and model created successfully.");
      console.log(response);

    } catch (error) {
      const message = error.response?.data?.error || "Failed to create client and model.";
      notify("error", message);
      console.error("Base submission failed:", error);
    }
  };

  const handleLinkingSubmit = async (e) => {
    e.preventDefault();
    setNotification(null);

    try {
      const response = await submitBulkWorkflow({
        type: "single_client",
        step: "linking",
        batch_code: batchcode,
        client: client,
        version: version,
        model: model
      });

      setBatchCode("");
      setClient("");
      setVersion("");
      setModel("");
      setLinkingCreated(true);

      notify("success", response.message || "Batch code and version created successfully.");
      console.log(response);
    } catch (error) {
      const message = error.response?.data?.error || "Failed to create batch code and version.";
      notify("error", message);
      console.error("Linking submission failed:", error);
    }
  };

  // Bulk clients handlers
  const handleBulkBaseChange = (index, field, value) => {
    const updated = [...bulkBase];
    updated[index][field] = value;
    setBulkBase(updated);
  };

  const handleBulkLinkingChange = (index, field, value) => {
    const updated = [...bulkLinking];
    updated[index][field] = value;
    setBulkLinking(updated);
  };

  const handleBulkBaseSubmit = async (e) => {
    e.preventDefault();
    setNotification(null);
    try {
      const response = await submitBulkWorkflow({
        type: "bulk_clients",
        step: "base",
        clients: bulkBase
      });

      setClientOptions(response.clients || []);
      setModelOptions(response.models  || []);
      setBulkBaseCreated(true);

      notify("success", response.message || "Bulk clients and models created successfully.");
      console.log(response);

    } catch (error) {
      const message = error.response?.data?.error || "Failed to create bulk clients and models.";
      notify("error", message);
      console.error("Bulk base submission failed:", error);
    }
  };

  const handleBulkLinkingSubmit = async (e) => {
    e.preventDefault();
    setNotification(null);
    try {
      const response = await submitBulkWorkflow({
        type: "bulk_clients",
        step: "linking",
        links: bulkLinking
      });

      setBulkLinking([
        { batch_code: "", client: "", version: "", model: "" },
        { batch_code: "", client: "", version: "", model: "" },
        { batch_code: "", client: "", version: "", model: "" },
      ]);

      setBulkBaseCreated(false);
      setBulkLinkingCreated(true);

      notify("success", response.message || "Bulk batch codes and versions created successfully.");
      console.log(response);
    } catch (error) {
      const message = error.response?.data?.error || "Failed to create bulk batch codes and versions.";
      notify("error", message);
      console.error("Bulk linking submission failed:", error);
    }
  };

  // Existing client — model selection fetches versions
  const handleExistingModelChange = async (modelId) => {
    setExistingModel(modelId);
    setExistingVersion("");
    setVersionOptions([]);
    if (!modelId) return;

    try {
      const versions = await getVersionsByModel(modelId);
      setVersionOptions(versions);
    } catch (error) {
      notify("error", "Failed to fetch versions.");
      console.error("Failed to fetch versions:", error);
    }
  };

  // Existing client — linking submit
  // Handles all three scenarios:
  // 1. Existing model + existing version + new batch code
  // 2. Existing model + new version + new batch code
  // 3. New model + new version + new batch code
  const handleExistingLinkingSubmit = async (e) => {
    e.preventDefault();
    setNotification(null);

    const isNewModel = modelMode === "new";
    const isNewVersion = versionMode === "new" || isNewModel;

    try {
      if (isNewModel) {
        // Step 1 — create the new model first
        const baseResponse = await submitBulkWorkflow({
          type: "single_client",
          step: "base",
          client_name: clientOptions.find(c => c.id === parseInt(existingClient))?.client_name || "",
          client_status: "Active",
          model_name: newModelName,
          model_status: newModelStatus
        });

        // Get the new model id from response
        const createdModel = baseResponse.models?.find(m => m.model_name === newModelName.trim().toLowerCase());
        if (!createdModel) throw new Error("Failed to resolve new model.");

        // Step 2 — link with new version and batch code
        const linkResponse = await submitBulkWorkflow({
          type: "single_client",
          step: "linking",
          batch_code: existingBatchCode,
          client: existingClient,
          version: newVersion,
          model: createdModel.id
        });

        notify("success", linkResponse.message || "New model, version and batch code created successfully.");
        console.log(linkResponse);

      } else {
        // Existing model — new or existing version
        const response = await submitBulkWorkflow({
          type: "single_client",
          step: "linking",
          batch_code: existingBatchCode,
          client: existingClient,
          version: isNewVersion ? newVersion : existingVersion,
          model: existingModel
        });

        notify("success", response.message || "Batch code created successfully.");
        console.log(response);
      }

      setExistingBatchCode("");
      setExistingLinkingCreated(true);

    } catch (error) {
      const message = error.response?.data?.error || error.message || "Failed to create batch code.";
      notify("error", message);
      console.error("Existing linking failed:", error);
    }
  };

  // Scan — fires on Enter key (covers barcode scanner and manual entry)
  const handleSerialKeyDown = async (e) => {
    if (e.key !== "Enter") return;
    e.preventDefault();
    if (!serialNumber.trim()) return;

    if (scannedDevices.some(d => d.serial_number === serialNumber.trim())) {
      notify("error", `${serialNumber.trim()} has already been scanned.`);
      return;
    }

    setNotification(null);

    try {
      const response = await submitScanWorkflow({
        type: "scan",
        serial_number: serialNumber
      });

      setScannedDevices(prev => [...prev, response.device]);
      setSerialNumber("");
      console.log(response);
    } catch (error) {
      const message = error.response?.data?.error || "Failed to scan device.";
      notify("error", message);
      console.error("Scan failed:", error.response?.data);
    }
  };

  // Remove a scanned device from the list
  const handleRemove = (serial_number) => {
    setScannedDevices(prev => prev.filter(d => d.serial_number !== serial_number));
  };

  // Save All — confirm all scanned devices in one API call
  const handleSaveAll = async () => {
    if (scannedDevices.length === 0) return;
    setNotification(null);

    try {
      const response = await submitDeviceWorkflow({
        type: "confirm_bulk",
        serial_numbers: scannedDevices.map(d => d.serial_number)
      });

      setScannedDevices([]);
      setSerialNumber("");

      notify("success", response.message || "All devices saved and activated.");
      console.log(response);

    } catch (error) {
      const message = error.response?.data?.error || "Failed to save devices.";
      notify("error", message);
      console.error("Save all failed:", error);
    }
  };

  // Scan unlocked when linking done or existing client linking done
  const scanUnlocked = linkingCreated || bulkLinkingCreated || scanReady || existingLinkingCreated;

  // Reset all existing client state
  const resetExistingClient = () => {
    setExistingClient("");
    setExistingModel("");
    setExistingVersion("");
    setExistingBatchCode("");
    setModelOptions2([]);
    setVersionOptions([]);
    setModelMode("existing");
    setVersionMode("existing");
    setNewModelName("");
    setNewModelStatus("");
    setNewVersion("");
    setExistingLinkingCreated(false);
  };

  return (
    <div className="bulk-workflow">
      <header className="bulk-workflow__header">
        <h1 className="bulk-workflow__title">Client Workflow</h1>
        <p className="bulk-workflow__subtitle">Add clients, link batch codes, and scan devices</p>
      </header>

      {/* Notification banner */}
      {notification && (
        <div className={`bulk-workflow__notification bulk-workflow__notification--${notification.type}`} style={{textAlign: "center", marginTop: "1rem"}}>
          {notification.message}
        </div>
      )}

      <select
        className="bulk-workflow__mode-select"
        value={mode}
        onChange={(e) => {
          setMode(e.target.value);
          setBaseCreated(false);
          setBulkBaseCreated(false);
          setLinkingCreated(false);
          setBulkLinkingCreated(false);
          setScannedDevices([]);
          setSerialNumber("");
          setClientOptions([]);
          setModelOptions([]);
          setScanReady(false);
          setNotification(null);
          resetExistingClient();
        }}
      >
        <option value="">Select Mode</option>
        <option value="single_client">Single Client</option>
        <option value="bulk_clients">Bulk Clients</option>
        <option value="existing_client">Existing Client</option>
      </select>

      {/* Single Client Mode */}
      {mode === "single_client" && (
        <section className="bulk-workflow__section">
          <form className="bulk-workflow__card" onSubmit={handleBaseSubmit}>
            <h2 className="bulk-workflow__card-title">Single Client</h2>
            <div className="bulk-workflow__fields">
              <div className="bulk-workflow__field">
                <input placeholder="Client Name" value={clientName} onChange={(e) => setClientName(e.target.value)} />
              </div>
              <div className="bulk-workflow__field">
                <input placeholder="Client Status" value={clientStatus} onChange={(e) => setClientStatus(e.target.value)} />
              </div>
              <div className="bulk-workflow__field">
                <input placeholder="Model Name" value={modelName} onChange={(e) => setModelName(e.target.value)} />
              </div>
              <div className="bulk-workflow__field">
                <input placeholder="Model Status" value={modelStatus} onChange={(e) => setModelStatus(e.target.value)} />
              </div>
            </div>
            <div className="bulk-workflow__actions">
              <button type="submit" className="bulk-workflow__btn bulk-workflow__btn--primary" disabled={baseCreated}>
                Add Client & Model
              </button>
            </div>
          </form>

          <form className="bulk-workflow__card" onSubmit={handleLinkingSubmit}>
            <h2 className="bulk-workflow__card-subtitle">Linking</h2>
            <div className="bulk-workflow__fields">
              <div className="bulk-workflow__field">
                <input placeholder="Batch Code" value={batchcode} onChange={(e) => setBatchCode(e.target.value)} disabled={!baseCreated} />
              </div>
              <div className="bulk-workflow__field">
                <select value={client} onChange={(e) => setClient(e.target.value)} disabled={!baseCreated}>
                  <option value="">Select Client</option>
                  {clientOptions.map((c) => (
                    <option key={c.id} value={c.id}>{c.client_name}</option>
                  ))}
                </select>
              </div>
              <div className="bulk-workflow__field">
                <input placeholder="Version" value={version} onChange={(e) => setVersion(e.target.value)} disabled={!baseCreated} />
              </div>
              <div className="bulk-workflow__field">
                <select value={model} onChange={(e) => setModel(e.target.value)} disabled={!baseCreated}>
                  <option value="">Select Model</option>
                  {modelOptions.map((m) => (
                    <option key={m.id} value={m.id}>{m.model_name}</option>
                  ))}
                </select>
              </div>
            </div>
            <div className="bulk-workflow__actions">
              <button type="submit" className="bulk-workflow__btn bulk-workflow__btn--primary" disabled={!baseCreated || linkingCreated}>
                Create Batch Code & Version
              </button>
            </div>
          </form>
        </section>
      )}

      {/* Bulk Clients Mode */}
      {mode === "bulk_clients" && (
        <section className="bulk-workflow__section">
          <form className="bulk-workflow__card" onSubmit={handleBulkBaseSubmit}>
            <h2 className="bulk-workflow__card-title">Bulk Clients</h2>
            {bulkBase.map((entry, index) => (
              <div key={index} className="bulk-workflow__entry">
                <h3 className="bulk-workflow__entry-title">Client {index + 1}</h3>
                <div className="bulk-workflow__fields">
                  <div className="bulk-workflow__field">
                    <input placeholder="Client Name" value={entry.client_name} onChange={(e) => handleBulkBaseChange(index, "client_name", e.target.value)} />
                  </div>
                  <div className="bulk-workflow__field">
                    <input placeholder="Client Status" value={entry.client_status} onChange={(e) => handleBulkBaseChange(index, "client_status", e.target.value)} />
                  </div>
                  <div className="bulk-workflow__field">
                    <input placeholder="Model Name" value={entry.model_name} onChange={(e) => handleBulkBaseChange(index, "model_name", e.target.value)} />
                  </div>
                  <div className="bulk-workflow__field">
                    <input placeholder="Model Status" value={entry.model_status} onChange={(e) => handleBulkBaseChange(index, "model_status", e.target.value)} />
                  </div>
                </div>
              </div>
            ))}
            <div className="bulk-workflow__actions">
              <button type="submit" className="bulk-workflow__btn bulk-workflow__btn--primary" disabled={bulkBaseCreated}>
                Add All Clients & Models
              </button>
            </div>
          </form>

          <form className="bulk-workflow__card" onSubmit={handleBulkLinkingSubmit}>
            <h2 className="bulk-workflow__card-subtitle">Linking</h2>
            {bulkLinking.map((entry, index) => (
              <div key={index} className="bulk-workflow__entry">
                <h3 className="bulk-workflow__entry-title">Linking {index + 1}</h3>
                <div className="bulk-workflow__fields">
                  <div className="bulk-workflow__field">
                    <input placeholder="Batch Code" value={entry.batch_code} onChange={(e) => handleBulkLinkingChange(index, "batch_code", e.target.value)} disabled={!bulkBaseCreated} />
                  </div>
                  <div className="bulk-workflow__field">
                    <select value={entry.client} onChange={(e) => handleBulkLinkingChange(index, "client", e.target.value)} disabled={!bulkBaseCreated}>
                      <option value="">Select Client</option>
                      {clientOptions.map((c) => (
                        <option key={c.id} value={c.id}>{c.client_name}</option>
                      ))}
                    </select>
                  </div>
                  <div className="bulk-workflow__field">
                    <input placeholder="Version" value={entry.version} onChange={(e) => handleBulkLinkingChange(index, "version", e.target.value)} disabled={!bulkBaseCreated} />
                  </div>
                  <div className="bulk-workflow__field">
                    <select value={entry.model} onChange={(e) => handleBulkLinkingChange(index, "model", e.target.value)} disabled={!bulkBaseCreated}>
                      <option value="">Select Model</option>
                      {modelOptions.map((m) => (
                        <option key={m.id} value={m.id}>{m.model_name}</option>
                      ))}
                    </select>
                  </div>
                </div>
              </div>
            ))}
            <div className="bulk-workflow__actions">
              <button type="submit" className="bulk-workflow__btn bulk-workflow__btn--primary" disabled={!bulkBaseCreated}>
                Create All Batch Codes & Versions
              </button>
            </div>
          </form>
        </section>
      )}

      {/* Existing Client Mode */}
      {mode === "existing_client" && (
        <section className="bulk-workflow__section">
          <div className="bulk-workflow__card">
            <h2 className="bulk-workflow__card-title">Existing Client</h2>
            <div className="bulk-workflow__fields">

              {/* Client — always a dropdown */}
              <div className="bulk-workflow__field">
                <select value={existingClient} onChange={(e) => setExistingClient(e.target.value)}>
                  <option value="">Select Client</option>
                  {clientOptions.map((c) => (
                    <option key={c.id} value={c.id}>{c.client_name}</option>
                  ))}
                </select>
              </div>

              {/* Model toggle */}
              {existingClient && (
                <div className="bulk-workflow__field">
                  <select value={modelMode} onChange={(e) => { setModelMode(e.target.value); setExistingModel(""); setNewModelName(""); setNewModelStatus(""); setVersionOptions([]); setExistingVersion(""); setNewVersion(""); }}>
                    <option value="existing">Existing Model</option>
                    <option value="new">New Model</option>
                  </select>
                </div>
              )}
            </div>

            {/* Existing model dropdown */}
            {existingClient && modelMode === "existing" && (
              <div className="bulk-workflow__fields" style={{marginTop: "0.75rem"}}>
                <div className="bulk-workflow__field">
                  <select value={existingModel} onChange={(e) => handleExistingModelChange(e.target.value)}>
                    <option value="">Select Model</option>
                    {modelOptions2.map((m) => (
                      <option key={m.id} value={m.id}>{m.model_name}</option>
                    ))}
                  </select>
                </div>

                {/* Version toggle — only shown after model is selected */}
                {existingModel && (
                  <div className="bulk-workflow__field">
                    <select value={versionMode} onChange={(e) => { setVersionMode(e.target.value); setExistingVersion(""); setNewVersion(""); }}>
                      <option value="existing">Existing Version</option>
                      <option value="new">New Version</option>
                    </select>
                  </div>
                )}

                {existingModel && versionMode === "existing" && (
                  <div className="bulk-workflow__field">
                    <select value={existingVersion} onChange={(e) => setExistingVersion(e.target.value)}>
                      <option value="">Select Version</option>
                      {versionOptions.map((v) => (
                        <option key={v.id} value={v.id}>{v.version}</option>
                      ))}
                    </select>
                  </div>
                )}

                {existingModel && versionMode === "new" && (
                  <div className="bulk-workflow__field">
                    <input placeholder="New Version" value={newVersion} onChange={(e) => setNewVersion(e.target.value)} />
                  </div>
                )}
              </div>
            )}

            {/* New model fields */}
            {existingClient && modelMode === "new" && (
              <div className="bulk-workflow__fields" style={{marginTop: "0.75rem"}}>
                <div className="bulk-workflow__field">
                  <input placeholder="New Model Name" value={newModelName} onChange={(e) => setNewModelName(e.target.value)} />
                </div>
                <div className="bulk-workflow__field">
                  <input placeholder="Model Status" value={newModelStatus} onChange={(e) => setNewModelStatus(e.target.value)} />
                </div>
                <div className="bulk-workflow__field">
                  <input placeholder="New Version" value={newVersion} onChange={(e) => setNewVersion(e.target.value)} />
                </div>
              </div>
            )}
          </div>

          {/* Linking form — shown when model and version are selected/entered */}
          {existingClient && (
            (modelMode === "existing" && existingModel && (versionMode === "existing" ? existingVersion : newVersion)) ||
            (modelMode === "new" && newModelName && newModelStatus && newVersion)
          ) && (
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
              <div className="bulk-workflow__actions">
                <button
                  type="submit"
                  className="bulk-workflow__btn bulk-workflow__btn--primary"
                  disabled={!existingBatchCode || existingLinkingCreated}
                >
                  Create Batch Code
                </button>
              </div>
            </form>
          )}
        </section>
      )}

      {/* Scan SN — unlocked after linking or existing client selected */}
      {mode && (
        <section className="bulk-workflow__scan">
          <div className="bulk-workflow__card">
            <h2 className="bulk-workflow__card-title">Scan Device</h2>

            <div className="bulk-workflow__field">
              <input
                placeholder="Scan or type serial number and press Enter"
                value={serialNumber}
                onChange={(e) => setSerialNumber(e.target.value)}
                onKeyDown={handleSerialKeyDown}
                disabled={!scanUnlocked}
              />
            </div>

            {scannedDevices.length > 0 && (
              <div className="bulk-workflow__device-details">
                <table className="bulk-workflow__device-table">
                  <thead>
                    <tr>
                      <th>Serial Number</th>
                      <th>Client</th>
                      <th>Batch Code</th>
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

                <div className="bulk-workflow__actions">
                  <button
                    type="button"
                    className="bulk-workflow__btn bulk-workflow__btn--primary"
                    onClick={handleSaveAll}
                  >
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