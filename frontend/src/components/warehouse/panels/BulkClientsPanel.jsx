import { useState, useEffect, useCallback, useMemo } from "react";
import {
  getExistingModels,
  getVersionsByModel, // your existing "versions of a model" call (ModelVersionListView); rename if yours differs
  getClientsAwaitingLinking,
  submitBulkClientsBase,
  submitBulkClientsLinking,
} from "../../../services/ClientApi";
import Notification, { useNotification } from "../shared/Notifications";
import ScanCard from "../shared/ScanCard";

const MAX_ROWS = 5;
const LINK_ERROR_FIELD_ORDER = ["batch_code", "client", "version", "model"];

// Same normalisation as the serializers (strip + lowercase), so the live checks
// agree with what the server will decide.
const normalise = (s) => (s ?? "").trim().toLowerCase();

// One row index drives both forms: the Add Clients row and the matching Linking row.
// Adding or removing a row changes both, so the two forms always have the same number of rows.
const blankRow = () => ({
  client_name: "", // Add Clients
  model_name: "", // Add Clients (optional: leave blank when the model already exists)
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

  // Existing versions of each model selected in Linking: { [modelId]: [{ id, version }] }
  const [versionsByModel, setVersionsByModel] = useState({});

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

  // Load the existing versions of every model currently selected in Linking.
  // The key only changes when the set of selected models changes, so typing a
  // version does not trigger requests. It reloads when the panel becomes active again.
  const selectedModelKey = [...new Set(rows.map((r) => r.model).filter(Boolean))]
    .sort()
    .join(",");

  useEffect(() => {
    if (!active || !selectedModelKey) return;
    let cancelled = false;
    (async () => {
      const loaded = {};
      await Promise.all(
        selectedModelKey.split(",").map(async (id) => {
          try {
            loaded[id] = await getVersionsByModel(id);
          } catch (error) {
            console.error("Failed to load versions for model", id, error);
          }
        })
      );
      if (!cancelled) setVersionsByModel(loaded);
    })();
    return () => {
      cancelled = true;
    };
  }, [active, selectedModelKey]);

  // ---- Live model check (Add Clients) ----
  const modelNames = useMemo(
    () => new Set(modelOptions.map((m) => normalise(m.model_name))),
    [modelOptions]
  );

  // One message per row, or null. These block Save because the server would reject them.
  const modelWarnings = rows.map((r, i) => {
    const typed = normalise(r.model_name);
    if (!typed) return null;
    if (modelNames.has(typed)) {
      return `"${r.model_name.trim()}" already exists. Leave this blank and select it in the Linking section.`;
    }
    const firstRow = rows.findIndex((o) => normalise(o.model_name) === typed);
    if (firstRow !== i) {
      return `Same model as row ${rowLabel(firstRow)}. Enter it once and select it in Linking for the other client.`;
    }
    return null;
  });
  const hasModelWarning = modelWarnings.some(Boolean);

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
      await loadLinkingData(); // the new clients and models now appear in the Linking dropdowns
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
                    placeholder="Model Name (optional)"
                    value={entry.model_name}
                    onChange={(e) => updateRow(index, "model_name", e.target.value)}
                  />
                  {modelWarnings[index] && (
                    <p style={{ fontSize: "0.75rem", color: "#b45309", margin: "0.25rem 0 0" }}>
                      {modelWarnings[index]}
                    </p>
                  )}
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
            <button
              type="submit"
              className="bulk-workflow__btn bulk-workflow__btn--primary"
              disabled={hasModelWarning}
              title={hasModelWarning ? "Fix the model warnings first" : ""}
            >
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

            // Existing versions of the model picked in this row. An existing version is valid:
            // versions are shared, so it is only a hint to pick it from the list.
            const versions = versionsByModel[entry.model] ?? [];
            const typedVersion = normalise(entry.version);
            const versionExists =
              !!typedVersion && versions.some((v) => normalise(v.version) === typedVersion);

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
                        list={`versions-${index}`}
                        value={entry.version}
                        onChange={(e) => updateRow(index, "version", e.target.value)}
                      />
                      <datalist id={`versions-${index}`}>
                        {versions.map((v) => (
                          <option key={v.id} value={v.version} />
                        ))}
                      </datalist>
                      {versionExists && (
                        <p style={{ fontSize: "0.75rem", color: "#2563eb", margin: "0.25rem 0 0" }}>
                          This version already exists for the model. Pick it from the list and it will be reused.
                        </p>
                      )}
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