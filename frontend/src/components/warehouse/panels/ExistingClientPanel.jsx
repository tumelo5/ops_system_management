import { useState, useEffect, useCallback, useMemo } from "react";
import {
  getExistingClients,
  getExistingModels,
  getVersionsByModel,
  validateExistingSelection,
  submitExistingClientBatch,
} from "../../../services/ClientApi";
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
  const [validatedBatchCode, setValidatedBatchCode] = useState(""); // batch the scan will use
  const [batchReady, setBatchReady] = useState(false); // a batch exists for this selection -> scan unlocked
  // Reveals the Linking card: the product is new, or the client has no batch for it yet
  const [selectionConfirmed, setSelectionConfirmed] = useState(false);

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

  // Only trust loaded versions that belong to the model currently typed
  const versionsLoading = !!modelKey && loadedVersions.model !== modelKey;
  const versionOptions = loadedVersions.model === modelKey ? loadedVersions.items : [];

  // The model/version row, when both already exist. Its id is what the server validates.
  const existingProduct =
    modelExists && typedVersion
      ? versionOptions.find((v) => normalise(v.version) === typedVersion)
      : undefined;
  const versionIsNew = modelExists && !!typedVersion && !versionsLoading && !existingProduct;

  // Load the existing versions whenever the typed model is one that exists
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

  // If the selection changes after a batch was confirmed, the old confirmation no longer applies
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

  // After Save All the cycle is complete: clear the selection and pick up any new models/versions
  const handleScanSaved = () => {
    resetSelection();
    loadOptions();
  };

  // Confirm the selection.
  // New model or version: no batch can exist yet, so open the Linking card.
  // Existing model and version: ask the server whether this client already has a batch for it.
  const handleConfirmSelection = async () => {
    clearNote();
    if (!existingProduct) {
      setSelectionConfirmed(true);
      return;
    }
    try {
      const response = await validateExistingSelection({ client, version: existingProduct.id });
      if (response.batch_exists) {
        setValidatedBatchCode(response.batch_code);
        setBatchReady(true);
        notify("success", response.message);
      } else {
        setSelectionConfirmed(true);
      }
    } catch (error) {
      notify("error", error.response?.data?.error || "Failed to validate selection.");
      console.error("Validate selection failed:", error);
    }
  };

  // Linking: a new batch code for this client and product. The server reuses the model and
  // version if they exist and creates them if they do not.
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
      loadOptions(); // a new model (if any) is now in the list
    } catch (error) {
      notify("error", error.response?.data?.error || error.message || "Failed to create batch code.");
      console.error("Existing linking failed:", error);
    }
  };

  const canConfirm = !!client && !!typedModel && !!typedVersion && !versionsLoading;
  const showHints = !selectionConfirmed && !batchReady;

  return (
    <div style={active ? undefined : { display: "none" }}>
      <section className="bulk-workflow__section">
        <div className="bulk-workflow__card">
          <h2 className="bulk-workflow__card-title">Existing Client</h2>

          {/* Suggestions: every existing model name, and the versions of the model typed */}
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
              <select value={client} onChange={(e) => setClient(e.target.value)}>
                <option value="">Select Client</option>
                {clientOptions.map((c) => (
                  <option key={c.id} value={c.id}>{c.client_name}</option>
                ))}
              </select>
            </div>

            {client && (
              <>
                <div className="bulk-workflow__field">
                  <input
                    placeholder="Model (pick or type)"
                    list="existing-model-names"
                    value={modelName}
                    onChange={(e) => setModelName(e.target.value)}
                  />
                </div>
                <div className="bulk-workflow__field">
                  <input
                    placeholder="Version (pick or type)"
                    list="existing-version-names"
                    value={version}
                    onChange={(e) => setVersion(e.target.value)}
                  />
                </div>
              </>
            )}
          </div>

          {/* What the selection will do */}
          {client && showHints && modelIsNew && typedVersion && (
            <p style={{ fontSize: "0.75rem", color: "#b45309", margin: "0.5rem 0 0" }}>
              "{modelName.trim()}" is a new model and will be created with this version. Check the spelling.
            </p>
          )}
          {client && showHints && versionIsNew && (
            <p style={{ fontSize: "0.75rem", color: "#2563eb", margin: "0.5rem 0 0" }}>
              This is a new version of an existing model.
            </p>
          )}
          {client && showHints && existingProduct && (
            <p style={{ fontSize: "0.75rem", color: "#2563eb", margin: "0.5rem 0 0" }}>
              This model and version already exist.
            </p>
          )}

          {/* Confirm: unlock scan, or open the Linking card */}
          {client && !batchReady && !selectionConfirmed && (
            <div style={{ marginTop: "0.5rem" }}>
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
        </div>

        {/* Linking card — a new product, or an existing one this client has no batch for yet */}
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