import { useState, useEffect, useCallback } from "react";
import {
  getExistingModels,
  getClientsAwaitingLinking,
  submitBulkClientsBase,
  submitBulkClientsLinking,
} from "../../../services/ClientApi";
import Notification, { useNotification } from "../shared/Notifications";
import ScanCard from "../shared/ScanCard";

const MAX_ROWS = 5;
const LINK_ERROR_FIELD_ORDER = ["batch_code", "client", "version", "model"];

// One row index drives both forms: the Add Clients row and the matching Linking row.
// Adding or removing a row changes both, so the two forms always have the same number of rows.
const blankRow = () => ({
  client_name: "", // Add Clients
  model_name: "", // Add Clients
  client: "", // Linking
  model: "", // Linking
  batch_code: "", // Linking
  version: "", // Linking
});

const rowLabel = (i) => `#${i + 1}`;

export default function BulkClientsPanel({ active, onDataChanged }) {
  const [rows, setRows] = useState([blankRow(), blankRow()]);

  // Dropdown data. Clients are only those that have no batch code yet.
  const [pendingClients, setPendingClients] = useState([]);
  const [modelOptions, setModelOptions] = useState([]);

  // Scan unlocks once a batch has been created in this panel
  const [scanUnlocked, setScanUnlocked] = useState(false);

  const [baseNote, notifyBase] = useNotification();
  const [linkNote, notifyLink] = useNotification();

  const loadLinkingData = useCallback(async () => {
    try {
      const [pending, models] = await Promise.all([
        getClientsAwaitingLinking(),
        getExistingModels(),
      ]);
      setPendingClients(pending);
      setModelOptions(models);
      // Drop any client selection that is no longer pending (e.g. linked in the meantime)
      setRows((prev) =>
        prev.map((r) =>
          r.client && !pending.some((c) => String(c.id) === String(r.client))
            ? { ...r, client: "" }
            : r
        )
      );
    } catch (error) {
      notifyLink("error", "Failed to load clients awaiting linking.");
      console.error("Failed to load linking data:", error);
    }
  }, [notifyLink]);

  // Refresh whenever the panel becomes the active mode (including coming back from Correct Info)
  useEffect(() => {
    if (active) loadLinkingData();
  }, [active, loadLinkingData]);

  // ---- Rows ----
  const updateRow = (index, field, value) =>
    setRows((prev) => prev.map((r, i) => (i === index ? { ...r, [field]: value } : r)));

  const addRow = () =>
    setRows((prev) => (prev.length >= MAX_ROWS ? prev : [...prev, blankRow()]));

  const removeRow = (index) =>
    setRows((prev) => (prev.length === 1 ? prev : prev.filter((_, i) => i !== index)));

  // ---- Add Clients and Models ----
  const handleBaseSubmit = async (e) => {
    e.preventDefault();
    const clients = rows.map(({ client_name, model_name }) => ({ client_name, model_name }));
    try {
      const response = await submitBulkClientsBase({ clients });
      // Clear only the Add Clients fields; the saved data can't be resubmitted
      setRows((prev) => prev.map((r) => ({ ...r, client_name: "", model_name: "" })));
      notifyBase("success", response.message || "Clients and models created.");
      await loadLinkingData(); // the new clients now appear in the Linking dropdowns
      onDataChanged?.();
    } catch (error) {
      notifyBase(
        "error",
        error.response?.data?.error || "Failed to create clients and models."
      );
    }
  };

  // ---- Linking ----
  const handleLinkSubmit = async (e) => {
    e.preventDefault();
    const links = rows.map(({ client, model, batch_code, version }) => ({
      client,
      model,
      batch_code,
      version,
    }));
    try {
      const response = await submitBulkClientsLinking({ links });
      // Clear only the Linking fields
      setRows((prev) =>
        prev.map((r) => ({ ...r, client: "", model: "", batch_code: "", version: "" }))
      );
      setScanUnlocked(true);
      notifyLink("success", response.message || "Batch codes and versions created.");
      await loadLinkingData(); // linked clients drop out of the dropdown
      onDataChanged?.();
    } catch (error) {
      const data = error.response?.data;
      let message = "Failed to create batch codes and versions.";
      if (data && typeof data === "object") {
        // First error in the order of the form layout
        const firstField = LINK_ERROR_FIELD_ORDER.find((f) => data[f]);
        if (firstField) {
          message = Array.isArray(data[firstField]) ? data[firstField][0] : data[firstField];
        } else if (data.error) {
          message = data.error;
        }
      }
      notifyLink("error", message);
      console.error("Bulk linking submission failed:", error);
    }
  };

  return (
    <div hidden={!active}>
      <section className="bulk-workflow__section">
        {/* Add Clients and Models */}
        <form className="bulk-workflow__card" onSubmit={handleBaseSubmit}>
          <h2 className="bulk-workflow__card-title">Add Clients and Models</h2>

          {rows.map((entry, index) => (
            <div
              key={index}
              className="bulk-workflow__entry"
              style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "0.5rem" }}
            >
              <span style={{ fontSize: "0.75rem", color: "#6b7280", minWidth: "1.5rem", textAlign: "right" }}>
                {rowLabel(index)}
              </span>
              <div className="bulk-workflow__fields bulk-workflow__fields--divided" style={{ flex: 1, margin: 0 }}>
                <div className="bulk-workflow__field">
                  <input
                    placeholder="Client Name"
                    value={entry.client_name}
                    onChange={(e) => updateRow(index, "client_name", e.target.value)}
                  />
                </div>
                <div className="bulk-workflow__field">
                  <input
                    placeholder="Model Name"
                    value={entry.model_name}
                    onChange={(e) => updateRow(index, "model_name", e.target.value)}
                  />
                </div>
              </div>
              {rows.length > 1 && (
                <button
                  type="button"
                  className="bulk-workflow__btn-remove"
                  onClick={() => removeRow(index)}
                  title="Remove row"
                  style={{ flexShrink: 0 }}
                >
                  🗑
                </button>
              )}
            </div>
          ))}

          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: "0.5rem" }}>
            <button
              type="button"
              className="bulk-workflow__btn bulk-workflow__btn--secondary"
              onClick={addRow}
              disabled={rows.length >= MAX_ROWS}
              title={rows.length >= MAX_ROWS ? "Maximum of 5 rows reached" : ""}
            >
              + Add Row {rows.length >= MAX_ROWS ? "(max)" : `(${rows.length}/${MAX_ROWS})`}
            </button>
            <button type="submit" className="bulk-workflow__btn bulk-workflow__btn--primary">
              Save Clients
            </button>
          </div>
          <Notification state={baseNote} />
        </form>

        {/* Linking: same rows as above; the client dropdown lists only clients without a batch code */}
        <form className="bulk-workflow__card" onSubmit={handleLinkSubmit}>
          <h2 className="bulk-workflow__card-subtitle">
            Linking (Batch Codes {"→"} Clients {"&"} Models {"→"} Model Versions)
          </h2>

          {pendingClients.length === 0 && (
            <p style={{ fontSize: "0.85rem", color: "#6b7280", margin: "0.5rem 0" }}>
              No clients are waiting for a batch code. Save new clients above to link them here.
            </p>
          )}

          {rows.map((entry, index) => {
            // A client picked in another row can't be picked again here
            const takenElsewhere = new Set(
              rows
                .filter((_, i) => i !== index)
                .map((r) => String(r.client))
                .filter(Boolean)
            );
            const clientChoices = pendingClients.filter((c) => !takenElsewhere.has(String(c.id)));

            return (
              <div
                key={index}
                className="bulk-workflow__entry"
                style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "0.5rem" }}
              >
                <span style={{ fontSize: "0.75rem", color: "#6b7280", minWidth: "1.5rem", textAlign: "right" }}>
                  {rowLabel(index)}
                </span>
                <div className="bulk-workflow__linking-fields" style={{ flex: 1 }}>
                  <div className="bulk-workflow__fields" style={{ margin: 0, marginBottom: "0.5rem" }}>
                    <div className="bulk-workflow__field">
                      <select
                        value={entry.client}
                        onChange={(e) => updateRow(index, "client", e.target.value)}
                      >
                        <option value="">Client</option>
                        {clientChoices.map((c) => (
                          <option key={c.id} value={c.id}>{c.client_name}</option>
                        ))}
                      </select>
                    </div>
                    <div className="bulk-workflow__field">
                      <select
                        value={entry.model}
                        onChange={(e) => updateRow(index, "model", e.target.value)}
                      >
                        <option value="">Model</option>
                        {modelOptions.map((m) => (
                          <option key={m.id} value={m.id}>{m.model_name}</option>
                        ))}
                      </select>
                    </div>
                  </div>
                  <div className="bulk-workflow__fields" style={{ margin: 0 }}>
                    <div className="bulk-workflow__field">
                      <input
                        placeholder="Batch Code"
                        value={entry.batch_code}
                        onChange={(e) => updateRow(index, "batch_code", e.target.value)}
                      />
                    </div>
                    <div className="bulk-workflow__field">
                      <input
                        placeholder="Version"
                        value={entry.version}
                        onChange={(e) => updateRow(index, "version", e.target.value)}
                      />
                    </div>
                  </div>
                </div>
              </div>
            );
          })}

          <div style={{ display: "flex", justifyContent: "flex-end", marginTop: "0.5rem" }}>
            <button
              type="submit"
              className="bulk-workflow__btn bulk-workflow__btn--primary"
              disabled={pendingClients.length === 0}
            >
              Save Links
            </button>
          </div>
          <Notification state={linkNote} />
        </form>
      </section>

      <ScanCard unlocked={scanUnlocked} />
    </div>
  );
}