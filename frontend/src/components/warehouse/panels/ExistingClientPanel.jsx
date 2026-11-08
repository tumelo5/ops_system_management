import { useState, useEffect, useCallback, useMemo } from "react";
import {
  getExistingClients,
  validateExistingSelection,
  submitExistingClientBatch,
} from "../../../services/ClientApi";
import { getExistingModels, getVersionsByModel } from "../../../services/ModelApi";
import Notification, { useNotification } from "../shared/Notifications";
import ScanCard from "../shared/ScanCard";

// Same normalisation as the serializers (strip + lowercase), so the live checks
// agree with what the server will decide.
const normalise = (s) => (s ?? "").trim().toLowerCase();

export default function ExistingClientPanel({ active }) {
  // Dropdown data (fetched from the server; never emptied by a reset)
  const [clientOptions, setClientOptions] = useState([]);
  const [modelOptions, setModelOptions] = useState([]); // [{ model }]
  // Versions of the model currently typed, tagged with the model they belong to
  const [loadedVersions, setLoadedVersions] = useState({ model: "", items: [] }); // items: [{ id, version }]

  // Selection: the model and version are picked from the lists or typed
  const [client, setClient] = useState("");
  const [modelName, setModelName] = useState("");
  const [version, setVersion] = useState("");
  const [batchCode, setBatchCode] = useState("");

  // Progress
  const [validatedBatchCode, setValidatedBatchCode] = useState("");
  const [batchReady, setBatchReady] = useState(false);
  // Reveals Linking when the product is new, or this client has no batch for it yet
  const [selectionConfirmed, setSelectionConfirmed] = useState(false);

  const [note, notify, clearNote] = useNotification();

  const loadOptions = useCallback(async () => {
    try {
      const [clients, models] = await Promise.all([
        getExistingClients(),
        getExistingModels(),
      ]);
      setClientOptions(clients);
      setModelOptions(models);
    } catch (error) {
      notify("error", "Failed to fetch existing data.");
      console.error("Failed to fetch existing data:", error);
    }
  }, [notify]);

  // Refresh whenever this panel becomes active.
  useEffect(() => {
    if (active) loadOptions();
  }, [active, loadOptions]);

  // ---- What the typed model and version mean ----
  const modelNames = useMemo(
    () => new Set(modelOptions.map((m) => normalise(m.model))),
    [modelOptions]
  );
  const typedModel = normalise(modelName);
  const typedVersion = normalise(version);

  const modelExists = !!typedModel && modelNames.has(typedModel);
  const modelIsNew = !!typedModel && !modelExists;
  const modelKey = modelExists ? typedModel : "";

  // Only trust loaded versions that belong to the model currently typed.
  const versionsLoading = !!modelKey && loadedVersions.model !== modelKey;
  const versionOptions =
    loadedVersions.model === modelKey ? loadedVersions.items : [];

  // The model/version row, when both already exist. Its id is what the server validates.
  const existingProduct =
    modelExists && typedVersion
      ? versionOptions.find((v) => normalise(v.version) === typedVersion)
      : undefined;
  const versionIsNew =
    modelExists && !!typedVersion && !versionsLoading && !existingProduct;

  // Load existing versions whenever the typed model is one that exists.
  useEffect(() => {
    if (!modelKey) return;

    let cancelled = false;

    (async () => {
      try {
        const data = await getVersionsByModel(modelKey);
        if (!cancelled) setLoadedVersions({ model: modelKey, items: data });
      } catch (error) {
        if (!cancelled) notify("error", "Failed to fetch versions.");
        console.error("Failed to fetch versions:", error);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [modelKey, notify]);

  // If the selection changes after a batch was confirmed, the old confirmation no longer applies.
  useEffect(() => {
    setBatchReady(false);
    setValidatedBatchCode("");
    setSelectionConfirmed(false);
  }, [client, modelName, version]);

  // Clears the selection only. Dropdown data is kept, then refreshed.
  const resetSelection = () => {
    setClient("");
    setModelName("");
    setVersion("");
    setBatchCode("");
    setValidatedBatchCode("");
    setLoadedVersions({ model: "", items: [] });
    setBatchReady(false);
    setSelectionConfirmed(false);
    clearNote();
  };

  // After Save All the cycle is complete: clear the selection and pick up new models/versions.
  const handleScanSaved = () => {
    resetSelection();
    loadOptions();
  };

  // New model or version: open Linking. Existing model/version: check for this client's batch.
  const handleConfirmSelection = async () => {
    clearNote();

    if (!existingProduct) {
      setSelectionConfirmed(true);
      return;
    }

    try {
      const response = await validateExistingSelection({
        client,
        version: existingProduct.id,
      });

      if (response.batch_exists) {
        setValidatedBatchCode(response.batch_code);
        setBatchReady(true);
        notify("success", response.message);
      } else {
        setSelectionConfirmed(true);
      }
    } catch (error) {
      notify(
        "error",
        error.response?.data?.error || "Failed to validate selection."
      );
      console.error("Validate selection failed:", error);
    }
  };

  // Create a new batch code for this client and product.
  const handleLinkingSubmit = async (e) => {
    e.preventDefault();
    clearNote();

    try {
      const response = await submitExistingClientBatch({
        client,
        model: modelName,
        version,
        batch_code: batchCode,
      });

      setValidatedBatchCode(batchCode);
      setBatchCode("");
      setBatchReady(true);
      notify("success", response.message || "Batch code created successfully.");
      loadOptions();
    } catch (error) {
      notify(
        "error",
        error.response?.data?.error ||
          error.message ||
          "Failed to create batch code."
      );
      console.error("Existing linking failed:", error);
    }
  };

  const canConfirm =
    !!client && !!typedModel && !!typedVersion && !versionsLoading;
  const showHints = !selectionConfirmed && !batchReady;

  return (
    <div className="existing-client" style={active ? undefined : { display: "none" }}>
      <section className="bulk-workflow__section">
        <div className="bulk-workflow__card">
          <div className="bulk-workflow__workflow-stage">
            <h2 className="bulk-workflow__card-title">Existing Client</h2>

            {/* Suggestions: every existing model name, and versions of the model typed. */}
            <datalist id="existing-model-names">
              {modelOptions.map((m) => (
                <option key={m.model} value={m.model} />
              ))}
            </datalist>

            <datalist id="existing-version-names">
              {versionOptions.map((v) => (
                <option key={v.id} value={v.version} />
              ))}
            </datalist>

            <div className="bulk-workflow__fields">
              <div className="bulk-workflow__field">
                <label className="bulk-workflow__field-label" htmlFor="existing-client">
                  Client
                </label>
                <select
                  id="existing-client"
                  value={client}
                  onChange={(e) => setClient(e.target.value)}
                >
                  <option value="">Select Client</option>
                  {clientOptions.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.client_name}
                    </option>
                  ))}
                </select>
              </div>

              {client && (
                <>
                  <div className="bulk-workflow__field">
                    <label className="bulk-workflow__field-label" htmlFor="existing-model">
                      Model
                    </label>
                    <input
                      id="existing-model"
                      placeholder="Pick or type model"
                      list="existing-model-names"
                      value={modelName}
                      onChange={(e) => setModelName(e.target.value)}
                    />
                  </div>

                  <div className="bulk-workflow__field">
                    <label className="bulk-workflow__field-label" htmlFor="existing-version">
                      Version
                    </label>
                    <input
                      id="existing-version"
                      placeholder="Pick or type version"
                      list="existing-version-names"
                      value={version}
                      onChange={(e) => setVersion(e.target.value)}
                    />
                  </div>
                </>
              )}
            </div>

            {/* Explain what the selection will do. */}
            {client && showHints && modelIsNew && typedVersion && (
              <p className="bulk-workflow__hint bulk-workflow__hint--warning">
                "{modelName.trim()}" is a new model and will be created with this
                version. Check the spelling.
              </p>
            )}

            {client && showHints && versionIsNew && (
              <p className="bulk-workflow__hint">
                This is a new version of an existing model.
              </p>
            )}

            {client && showHints && existingProduct && (
              <p className="bulk-workflow__hint">
                This model and version already exist.
              </p>
            )}

            {/* Confirm: unlock scanning, or reveal Linking. */}
            {client && !batchReady && !selectionConfirmed && (
              <div className="bulk-workflow__stage-actions">
                <div className="bulk-workflow__actions">
                  <button
                    type="button"
                    className="bulk-workflow__btn bulk-workflow__btn--primary"
                    onClick={handleConfirmSelection}
                    disabled={!canConfirm}
                  >
                    Confirm Selection
                  </button>
                </div>
                <Notification state={note} />
              </div>
            )}

            {/* The validated batch remains visible until the cycle is completed or selection changes. */}
            {validatedBatchCode && (
              <div className="bulk-workflow__batch-banner">
                ✓ {validatedBatchCode} — ready to scan
              </div>
            )}
          </div>

          {/* Linking belongs to the same workflow card, not a separate card. */}
          {selectionConfirmed && (
            <form
              className="bulk-workflow__subsection"
              onSubmit={handleLinkingSubmit}
            >
              <h3 className="bulk-workflow__card-subtitle">Linking</h3>

              <div className="bulk-workflow__fields">
                <div className="bulk-workflow__field">
                  <label className="bulk-workflow__field-label" htmlFor="existing-batch-code">
                    New Batch Code
                  </label>
                  <input
                    id="existing-batch-code"
                    placeholder="Enter batch code"
                    value={batchCode}
                    onChange={(e) => setBatchCode(e.target.value)}
                    disabled={batchReady}
                  />
                </div>
              </div>

              <div className="bulk-workflow__actions">
                <button
                  type="submit"
                  className="bulk-workflow__btn bulk-workflow__btn--primary"
                  disabled={!batchCode.trim() || batchReady}
                >
                  Create Batch Code
                </button>
              </div>

              <Notification state={note} />
            </form>
          )}

          {/* Scan Device is embedded in this card for this workflow. */}
          <ScanCard
            unlocked={batchReady}
            onSaved={handleScanSaved}
            embedded
          />
        </div>
      </section>
    </div>
  );
}
