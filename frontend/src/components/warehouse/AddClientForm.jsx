import { useState } from "react";
import { submitClientWorkflow } from "../../services/ClientApi";

export default function AddClientForm() {

  const [mode, setMode] = useState("");
  const [baseCreated, setBaseCreated] = useState(false);

  // Client
  const [clientName, setClientName] = useState("");
  const [clientStatus, setClientStatus] = useState("");

  // Model
  const [modelName, setModelName] = useState("");
  const [modelstatus, setModelStatus] = useState("");

  // Batch code
  const [batchcode, setBatchCode] = useState("");
  const [client, setClient] = useState("");

  // Version
  const [version, setVersion] = useState("");
  const [model, setModel] = useState("");

  // Dropdown data
  const [clientOptions, setClientOptions] = useState([]);
  const [modelOptions, setModelOptions] = useState([]);


  const handleBaseSubmit = async (e) => {
    e.preventDefault();

    try {
      const response = await submitClientWorkflow({
        type: "single_client",
        step: "base",
        client_name: clientName,
        client_status: clientStatus,
        model_name: modelName,
        model_status: modelstatus
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

    try {
      const response = await submitClientWorkflow({
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

      console.log(response);

    } catch (error) {
      console.error("Linking submission failed:", error);
    }
  };


  return (
    <>
      <h1>Client Workflow</h1>

      <select
        value={mode}
        onChange={(e) => {
          setMode(e.target.value);
          setBaseCreated(false);
          setClientOptions([]);
          setModelOptions([]);
        }}
      >
        <option value="">Select Mode</option>
        <option value="single_client">Single Client</option>
        <option value="bulk_clients">Bulk Clients</option>
      </select>


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
              value={modelstatus}
              onChange={(e) => setModelStatus(e.target.value)}
            />
            <button type="submit">Add Client & Model</button>
          </form>

          {/* Form 2 — linking step, locked until base is created */}
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
                <option key={c.id} value={c.id}>
                  {c.client_name}
                </option>
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
                <option key={m.id} value={m.id}>
                  {m.model_name}
                </option>
              ))}
            </select>

            <button type="submit" disabled={!baseCreated}>
              Create Batch Code & Version
            </button>
          </form>
        </>
      )}
    </>
  );
}