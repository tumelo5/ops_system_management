import { useState } from "react";
import { submitClientWorkflow } from "../../services/ClientApi";
import "../../styles/components/bulk-workflow.css";

export default function AddClientForm() {
  const [mode, setMode] = useState("");
  const [baseCreated, setBaseCreated] = useState(false);

  const [clientName, setClientName] = useState("");
  const [clientStatus, setClientStatus] = useState("");
  const [modelName, setModelName] = useState("");
  const [modelstatus, setModelStatus] = useState("");
  const [batchcode, setBatchCode] = useState("");
  const [client, setClient] = useState("");
  const [version, setVersion] = useState("");
  const [model, setModel] = useState("");
  const [clientOptions, setClientOptions] = useState([]);
  const [modelOptions, setModelOptions] = useState([]);

  const resetMode = () => {
    setBaseCreated(false);
    setClientOptions([]);
    setModelOptions([]);
  };

  const handleBaseSubmit = async (e) => {
    e.preventDefault();

    try {
      const response = await submitClientWorkflow({
        type: "single_client",
        step: "base",
        client_name: clientName,
        client_status: clientStatus,
        model_name: modelName,
        model_status: modelstatus,
      });

      setClientOptions(response.clients || []);
      setModelOptions(response.models || []);
      setClientName("");
      setClientStatus("");
      setModelName("");
      setModelStatus("");
      setBaseCreated(true);
    } catch (error) {
      console.error("Base submission failed:", error);
    }
  };

  const handleLinkingSubmit = async (e) => {
    e.preventDefault();

    try {
      await submitClientWorkflow({
        type: "single_client",
        step: "linking",
        batch_code: batchcode,
        client: client,
        version: version,
        model: model,
      });

      setBatchCode("");
      setClient("");
      setVersion("");
      setModel("");
    } catch (error) {
      console.error("Linking submission failed:", error);
    }
  };

  return (
    <div className="bulk-workflow">
      <header className="bulk-workflow__header">
        <h1 className="bulk-workflow__title">Client Workflow</h1>
        <p className="bulk-workflow__subtitle">Add a single client, model, and linking details</p>
      </header>

      <select
        className="bulk-workflow__mode-select"
        value={mode}
        onChange={(e) => {
          setMode(e.target.value);
          resetMode();
        }}
      >
        <option value="">Select Mode</option>
        <option value="single_client">Single Client</option>
        <option value="bulk_clients">Bulk Clients</option>
      </select>

      {mode === "single_client" && (
        <section className="bulk-workflow__section">
          <form className="bulk-workflow__card" onSubmit={handleBaseSubmit}>
            <h2 className="bulk-workflow__card-title">Single Client</h2>
            <div className="bulk-workflow__fields">
              <div className="bulk-workflow__field">
                <input
                  placeholder="Client Name"
                  value={clientName}
                  onChange={(e) => setClientName(e.target.value)}
                />
              </div>
              <div className="bulk-workflow__field">
                <input
                  placeholder="Client Status"
                  value={clientStatus}
                  onChange={(e) => setClientStatus(e.target.value)}
                />
              </div>
              <div className="bulk-workflow__field">
                <input
                  placeholder="Model Name"
                  value={modelName}
                  onChange={(e) => setModelName(e.target.value)}
                />
              </div>
              <div className="bulk-workflow__field">
                <input
                  placeholder="Model Status"
                  value={modelstatus}
                  onChange={(e) => setModelStatus(e.target.value)}
                />
              </div>
            </div>
            <div className="bulk-workflow__actions">
              <button type="submit" className="bulk-workflow__btn bulk-workflow__btn--primary">
                Add Client & Model
              </button>
            </div>
          </form>

          <form className="bulk-workflow__card" onSubmit={handleLinkingSubmit}>
            <h2 className="bulk-workflow__card-subtitle">Linking</h2>
            <div className="bulk-workflow__fields">
              <div className="bulk-workflow__field">
                <input
                  placeholder="Batch Code"
                  value={batchcode}
                  onChange={(e) => setBatchCode(e.target.value)}
                  disabled={!baseCreated}
                />
              </div>
              <div className="bulk-workflow__field">
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
              </div>
              <div className="bulk-workflow__field">
                <input
                  placeholder="Version"
                  value={version}
                  onChange={(e) => setVersion(e.target.value)}
                  disabled={!baseCreated}
                />
              </div>
              <div className="bulk-workflow__field">
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
              </div>
            </div>
            <div className="bulk-workflow__actions">
              <button
                type="submit"
                className="bulk-workflow__btn bulk-workflow__btn--primary"
                disabled={!baseCreated}
              >
                Create Batch Code & Version
              </button>
            </div>
          </form>
        </section>
      )}

      {mode === "bulk_clients" && (
        <section className="bulk-workflow__section">
          <div className="bulk-workflow__card">
            <p className="bulk-workflow__subtitle">
              Use the Bulk Clients tab on the Client Management page for bulk entry.
            </p>
          </div>
        </section>
      )}
    </div>
  );
}
