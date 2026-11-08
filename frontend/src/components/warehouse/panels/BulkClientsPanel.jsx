import { useState, useEffect, useCallback, useMemo } from "react";
import {
  getClientsAwaitingLinking,
  submitBulkClientsBase,
  submitBulkClientsLinking,
} from "../../../services/ClientApi";
import { getExistingModels, getVersionsByModel } from "../../../services/ModelApi";

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
  client_name: "",
  client: "",
  model: "",
  batch_code: "",
  version: "",
});

const rowLabel = (i) => `#${i + 1}`;

export default function BulkClientsPanel({ active, onDataChanged }) {
  const [rows, setRows] = useState([blankRow(), blankRow()]);

  // Dropdown data. Clients are only those that have no batch code yet.
  const [pendingClients, setPendingClients] = useState([]);
  const [modelOptions, setModelOptions] = useState([]);

  // Existing versions of the models typed in Linking:
  // { [normalisedModelName]: [{ id, version }] }
  const [versionsByModel, setVersionsByModel] = useState({});

  // Scan unlocks once a batch has been created in this panel.
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

      // Drop any client selection that is no longer pending (e.g. linked in the meantime).
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

  // Refresh whenever the panel becomes the active mode (including coming back from Correct Info).
  useEffect(() => {
    if (active) loadLinkingData();
  }, [active, loadLinkingData]);

  const modelNames = useMemo(
    () => new Set(modelOptions.map((m) => normalise(m.model))),
    [modelOptions]
  );

  // Load existing versions for every existing model typed in Linking.
  // The key only changes when the set of typed models changes.
  const typedExistingModels = [
    ...new Set(
      rows.map((r) => normalise(r.model)).filter((n) => n && modelNames.has(n))
    ),
  ].sort();
  const typedExistingModelsKey = JSON.stringify(typedExistingModels);

  useEffect(() => {
    if (!active) return;

    const names = JSON.parse(typedExistingModelsKey);
    if (names.length === 0) return;

    let cancelled = false;

    (async () => {
      const loaded = {};
      await Promise.all(
        names.map(async (name) => {
          try {
            loaded[name] = await getVersionsByModel(name);
          } catch (error) {
            console.error("Failed to load versions for model", name, error);
          }
        })
      );

      if (!cancelled) setVersionsByModel(loaded);
    })();

    return () => {
      cancelled = true;
    };
  }, [active, typedExistingModelsKey]);

  // ---- Rows ----
  const updateRow = (index, field, value) =>
    setRows((prev) =>
      prev.map((r, i) => (i === index ? { ...r, [field]: value } : r))
    );

  const addRow = () =>
    setRows((prev) => (prev.length >= MAX_ROWS ? prev : [...prev, blankRow()]));

  const removeRow = (index) =>
    setRows((prev) =>
      prev.length === 1 ? prev : prev.filter((_, i) => i !== index)
    );

  // ---- Add Clients ----
  const handleBaseSubmit = async (e) => {
    e.preventDefault();

    const clients = rows.map(({ client_name }) => ({ client_name }));

    try {
      const response = await submitBulkClientsBase({ clients });

      // Clear only the Add Clients fields; the saved data can't be resubmitted.
      setRows((prev) => prev.map((r) => ({ ...r, client_name: "" })));
      notifyBase("success", response.message || "Clients created.");
      await loadLinkingData();
      onDataChanged?.();
    } catch (error) {
      notifyBase(
        "error",
        error.response?.data?.error || "Failed to create clients."
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

      // Clear only the Linking fields.
      setRows((prev) =>
        prev.map((r) => ({
          ...r,
          client: "",
          model: "",
          batch_code: "",
          version: "",
        }))
      );
      setScanUnlocked(true);
      notifyLink(
        "success",
        response.message || "Batch codes and versions created."
      );
      await loadLinkingData();
      onDataChanged?.();
    } catch (error) {
      const data = error.response?.data;
      let message = "Failed to create batch codes and versions.";

      if (data && typeof data === "object") {
        // First error in the order of the form layout.
        const firstField = LINK_ERROR_FIELD_ORDER.find((field) => data[field]);

        if (firstField) {
          message = Array.isArray(data[firstField])
            ? data[firstField][0]
            : data[firstField];
        } else if (data.error) {
          message = data.error;
        }
      }

      notifyLink("error", message);
      console.error("Bulk linking submission failed:", error);
    }
  };

  return (
    <div hidden={!active} className="bulk-clients">
      <section className="bulk-workflow__section">
        {/* Add Clients */}
        <form className="bulk-workflow__card" onSubmit={handleBaseSubmit}>
          <h2 className="bulk-workflow__card-title">Add Clients</h2>

          <div className="bulk-clients__rows">
            {rows.map((entry, index) => (
              <div className="bulk-clients__entry" key={index}>
                <span className="bulk-clients__row-number">
                  {rowLabel(index)}
                </span>

                <div className="bulk-workflow__field bulk-clients__client-field">
                  <input
                    type="text"
                    placeholder="Client Name"
                    value={entry.client_name}
                    onChange={(e) =>
                      updateRow(index, "client_name", e.target.value)
                    }
                    aria-label={`Client name ${index + 1}`}
                  />
                </div>

                {rows.length > 1 && (
                  <button
                    type="button"
                    className="bulk-workflow__btn-remove"
                    onClick={() => removeRow(index)}
                    title="Remove row"
                    aria-label={`Remove client row ${index + 1}`}
                  >
                    🗑
                  </button>
                )}
              </div>
            ))}
          </div>

          <div className="bulk-clients__actions">
            <button
              type="button"
              className="bulk-workflow__btn bulk-workflow__btn--secondary"
              onClick={addRow}
              disabled={rows.length >= MAX_ROWS}
              title={
                rows.length >= MAX_ROWS ? "Maximum of 5 rows reached" : ""
              }
            >
              + Add Row{" "}
              {rows.length >= MAX_ROWS ? "(max)" : `(${rows.length}/${MAX_ROWS})`}
            </button>

            <button
              type="submit"
              className="bulk-workflow__btn bulk-workflow__btn--primary"
            >
              Save Clients
            </button>
          </div>

          <Notification state={baseNote} />
        </form>

        {/* Linking: the client dropdown lists only clients without a batch code. */}
        <form className="bulk-workflow__card" onSubmit={handleLinkSubmit}>
          <h2 className="bulk-workflow__card-subtitle">
            Linking (Batch Codes {"→"} Clients {"&"} Models {"→"} Model Versions)
          </h2>

          <datalist id="model-names">
            {modelOptions.map((m) => (
              <option key={m.model} value={m.model} />
            ))}
          </datalist>

          {pendingClients.length === 0 ? (
            <p className="bulk-clients__empty-state">
              No clients are waiting for a batch code. Save new clients above
              to link them here.
            </p>
          ) : (
            <>
              <div className="bulk-clients__rows bulk-clients__linking-rows">
                {rows.map((entry, index) => {
                  // A client picked in another row can't be picked again here.
                  const takenElsewhere = new Set(
                    rows
                      .filter((_, i) => i !== index)
                      .map((r) => String(r.client))
                      .filter(Boolean)
                  );
                  const clientChoices = pendingClients.filter(
                    (c) => !takenElsewhere.has(String(c.id))
                  );

                  // Live checks for this row.
                  const typedModel = normalise(entry.model);
                  const typedVersion = normalise(entry.version);
                  const modelExists =
                    !!typedModel && modelNames.has(typedModel);
                  const modelIsNew = !!typedModel && !modelExists;
                  const versions = modelExists
                    ? versionsByModel[typedModel] ?? []
                    : [];
                  const productExists =
                    modelExists &&
                    !!typedVersion &&
                    versions.some(
                      (v) => normalise(v.version) === typedVersion
                    );

                  return (
                    <div className="bulk-clients__entry" key={index}>
                      <span className="bulk-clients__row-number">
                        {rowLabel(index)}
                      </span>

                      <div className="bulk-clients__link-fields">
                        <div className="bulk-workflow__field">
                          <select
                            value={entry.client}
                            onChange={(e) =>
                              updateRow(index, "client", e.target.value)
                            }
                            aria-label={`Client for linking row ${index + 1}`}
                          >
                            <option value="">Client</option>
                            {clientChoices.map((c) => (
                              <option key={c.id} value={c.id}>
                                {c.client_name}
                              </option>
                            ))}
                          </select>
                        </div>

                        <div className="bulk-workflow__field">
                          <input
                            type="text"
                            placeholder="Model (pick or type)"
                            list="model-names"
                            value={entry.model}
                            onChange={(e) =>
                              updateRow(index, "model", e.target.value)
                            }
                            aria-label={`Model for linking row ${index + 1}`}
                          />
                          {modelIsNew && (
                            <p className="bulk-clients__field-hint bulk-clients__field-hint--warning">
                              "{entry.model.trim()}" is a new model and will be
                              created. Check the spelling.
                            </p>
                          )}
                        </div>

                        <div className="bulk-workflow__field">
                          <input
                            type="text"
                            placeholder="Batch Code"
                            value={entry.batch_code}
                            onChange={(e) =>
                              updateRow(index, "batch_code", e.target.value)
                            }
                            aria-label={`Batch code for linking row ${index + 1}`}
                          />
                        </div>

                        <div className="bulk-workflow__field">
                          <input
                            type="text"
                            placeholder="Version (pick or type)"
                            list={`versions-${index}`}
                            value={entry.version}
                            onChange={(e) =>
                              updateRow(index, "version", e.target.value)
                            }
                            aria-label={`Version for linking row ${index + 1}`}
                          />
                          <datalist id={`versions-${index}`}>
                            {versions.map((v) => (
                              <option key={v.id} value={v.version} />
                            ))}
                          </datalist>
                          {productExists && (
                            <p className="bulk-clients__field-hint bulk-clients__field-hint--info">
                              This model and version already exist and will be
                              reused.
                            </p>
                          )}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>

              <div className="bulk-clients__link-actions">
                <button
                  type="submit"
                  className="bulk-workflow__btn bulk-workflow__btn--primary"
                >
                  Save Links
                </button>
              </div>
            </>
          )}

          <Notification state={linkNote} />
        </form>
      </section>

      <ScanCard unlocked={scanUnlocked} />
    </div>
  );
}
