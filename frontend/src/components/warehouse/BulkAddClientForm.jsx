import { useState, useEffect } from "react";
import { submitBulkWorkflow, submitDeviceWorkflow, getExistingClients } from "../../services/ClientApi";


export default function BulkAddClientForm() {

  const [mode, setMode] = useState("");

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

  // Device capture
  const [serialNumber, setSerialNumber] = useState("");
  const [scanResult, setScanResult] = useState(null);
  const [scanReady, setScanReady] = useState(false);


  // Fetch existing clients when existing_client mode is selected
  useEffect(() => {
    if (mode !== "existing_client") return;

    const fetchClients = async () => {
      try {
        const clients = await getExistingClients();
        setClientOptions(clients);
        setScanReady(true);
      } catch (error) {
        console.error("Failed to fetch existing clients:", error);
      }
    };

    fetchClients();
  }, [mode]);


  // Single client handlers
  const handleBaseSubmit = async (e) => {
    e.preventDefault();

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

      console.log(response);

    } catch (error) {
      console.error("Base submission failed:", error);
    }
  };

  const handleLinkingSubmit = async (e) => {
    e.preventDefault();

    // debug to check what data is being sent
    console.log("linking payload:", {batchcode, client, version, model});

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
      setLinkingCreated(true); // unlock scan

      console.log(response);

    } catch (error) {
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

    try {
      const response = await submitBulkWorkflow({
        type: "bulk_clients",
        step: "base",
        clients: bulkBase
      });

      setClientOptions(response.clients || []);
      setModelOptions(response.models  || []);
      setBulkBaseCreated(true);

      console.log(response);

    } catch (error) {
      console.error("Bulk base submission failed:", error);
    }
  };

  const handleBulkLinkingSubmit = async (e) => {
    e.preventDefault();

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
      setBulkLinkingCreated(true); // unlock scan

      console.log(response);

    } catch (error) {
      console.error("Bulk linking submission failed:", error);
    }
  };


  // Device capture handlers
  const handleScan = async (e) => {
    e.preventDefault();

    try {
      const response = await submitDeviceWorkflow({
        type: "scan",
        serial_number: serialNumber
      });

      setScanResult(response.device);
      console.log(response);

    } catch (error) {
      console.error("Scan failed:", error.response?.data);
    }
  };

  const handleConfirm = async () => {
    try {
      const response = await submitDeviceWorkflow({
        type: "confirm",
        serial_number: scanResult.serial_number
      });

      setScanResult(null);
      setSerialNumber("");
      console.log(response);

    } catch (error) {
      console.error("Confirm failed:", error);
    }
  };


  // Scan is unlocked when linking is done (new) or existing client is selected
  const scanUnlocked = linkingCreated || bulkLinkingCreated || scanReady;


  return (
    <>
      <h1>Client Workflow</h1>

      <select
        value={mode}
        onChange={(e) => {
          setMode(e.target.value);
          setBaseCreated(false);
          setBulkBaseCreated(false);
          setLinkingCreated(false);
          setBulkLinkingCreated(false);
          setScanResult(null);
          setSerialNumber("");
          setClientOptions([]);
          setModelOptions([]);
          setScanReady(false);
        }}
      >
        <option value="">Select Mode</option>
        <option value="single_client">Single Client</option>
        <option value="bulk_clients">Bulk Clients</option>
        <option value="existing_client">Existing Client</option>
      </select>


      {/* Single Client Mode */}
      {mode === "single_client" && (
        <>
          {/* Form 1 — base step */}
          <form onSubmit={handleBaseSubmit}>
            <h2>Single Client</h2>
            <input
              placeholder="Client Name"
              value={clientName}
              onChange={(e) => setClientName(e.target.value)}
            />
            <input
              placeholder="Client Status"
              value={clientStatus}
              onChange={(e) => setClientStatus(e.target.value)}
            />
            <input
              placeholder="Model Name"
              value={modelName}
              onChange={(e) => setModelName(e.target.value)}
            />
            <input
              placeholder="Model Status"
              value={modelStatus}
              onChange={(e) => setModelStatus(e.target.value)}
            />
            <button type="submit">Add Client & Model</button>
          </form>

          {/* Form 2 — linking step */}
          <form onSubmit={handleLinkingSubmit}>
            <input
              placeholder="Batch Code"
              value={batchcode}
              onChange={(e) => setBatchCode(e.target.value)}
              disabled={!baseCreated}
            />
            <select
              value={client}
              onChange={(e) => setClient(e.target.value)}
              disabled={!baseCreated}
            >
              <option value="">Select Client</option>
              {clientOptions.map((c) => (
                <option key={c.id} value={c.id}>{c.client_name}</option>
              ))}
            </select>
            <input
              placeholder="Version"
              value={version}
              onChange={(e) => setVersion(e.target.value)}
              disabled={!baseCreated}
            />
            <select
              value={model}
              onChange={(e) => setModel(e.target.value)}
              disabled={!baseCreated}
            >
              <option value="">Select Model</option>
              {modelOptions.map((m) => (
                <option key={m.id} value={m.id}>{m.model_name}</option>
              ))}
            </select>
            <button type="submit" disabled={!baseCreated}>
              Create Batch Code & Version
            </button>
          </form>
        </>
      )}


      {/* Bulk Clients Mode */}
      {mode === "bulk_clients" && (
        <>
          {/* Form 1 — bulk base step */}
          <form onSubmit={handleBulkBaseSubmit}>
            <h2>Bulk Clients</h2>
            {bulkBase.map((entry, index) => (
              <div key={index}>
                <h3>Client {index + 1}</h3>
                <input
                  placeholder="Client Name"
                  value={entry.client_name}
                  onChange={(e) => handleBulkBaseChange(index, "client_name", e.target.value)}
                />
                <input
                  placeholder="Client Status"
                  value={entry.client_status}
                  onChange={(e) => handleBulkBaseChange(index, "client_status", e.target.value)}
                />
                <input
                  placeholder="Model Name"
                  value={entry.model_name}
                  onChange={(e) => handleBulkBaseChange(index, "model_name", e.target.value)}
                />
                <input
                  placeholder="Model Status"
                  value={entry.model_status}
                  onChange={(e) => handleBulkBaseChange(index, "model_status", e.target.value)}
                />
              </div>
            ))}
            <button type="submit">Add All Clients & Models</button>
          </form>

          {/* Form 2 — bulk linking step */}
          <form onSubmit={handleBulkLinkingSubmit}>
            {bulkLinking.map((entry, index) => (
              <div key={index}>
                <h3>Linking {index + 1}</h3>
                <input
                  placeholder="Batch Code"
                  value={entry.batch_code}
                  onChange={(e) => handleBulkLinkingChange(index, "batch_code", e.target.value)}
                  disabled={!bulkBaseCreated}
                />
                <select
                  value={entry.client}
                  onChange={(e) => handleBulkLinkingChange(index, "client", e.target.value)}
                  disabled={!bulkBaseCreated}
                >
                  <option value="">Select Client</option>
                  {clientOptions.map((c) => (
                    <option key={c.id} value={c.id}>{c.client_name}</option>
                  ))}
                </select>
                <input
                  placeholder="Version"
                  value={entry.version}
                  onChange={(e) => handleBulkLinkingChange(index, "version", e.target.value)}
                  disabled={!bulkBaseCreated}
                />
                <select
                  value={entry.model}
                  onChange={(e) => handleBulkLinkingChange(index, "model", e.target.value)}
                  disabled={!bulkBaseCreated}
                >
                  <option value="">Select Model</option>
                  {modelOptions.map((m) => (
                    <option key={m.id} value={m.id}>{m.model_name}</option>
                  ))}
                </select>
              </div>
            ))}
            <button type="submit" disabled={!bulkBaseCreated}>
              Create All Batch Codes & Versions
            </button>
          </form>
        </>
      )}


      {/* Existing Client Mode */}
      {mode === "existing_client" && (
        <>
          <h2>Existing Client</h2>
          <select
            value={client}
            onChange={(e) => setClient(e.target.value)}
          >
            <option value="">Select Client</option>
            {clientOptions.map((c) => (
              <option key={c.id} value={c.id}>{c.client_name}</option>
            ))}
          </select>
        </>
      )}


      {/* Scan SN — unlocked after linking or existing client selected */}
      {mode && (
        <div>
          <h2>Scan Device</h2>
          <form onSubmit={handleScan}>
            <input
              placeholder="Scan Serial Number"
              value={serialNumber}
              onChange={(e) => setSerialNumber(e.target.value)}
              disabled={!scanUnlocked}
            />
            <button type="submit" disabled={!scanUnlocked}>
              Scan
            </button>
          </form>

          {/* Staging snapshot — shown after scan */}
          {scanResult && (
            <div>
              <h3>Device Details</h3>
              <p>Serial Number: {scanResult.serial_number}</p>
              <p>Client: {scanResult.client_name}</p>
              <p>Batch Code: {scanResult.batch_code}</p>
              <p>Model: {scanResult.model_name}</p>
              <p>Version: {scanResult.version_name}</p>
              <p>Status: {scanResult.status}</p>
              <button onClick={handleConfirm}>Confirm & Activate</button>
            </div>
          )}
        </div>
      )}
    </>
  );
}