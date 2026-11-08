import React, { useState, useEffect, useCallback } from 'react';
import { getExistingClients, correctClient } from '../../../services/ClientApi';
import {
  getExistingModels,
  getVersionsByModel,
  correctModel,
  correctModelVersion,
} from '../../../services/ModelApi';

import Notification, { useNotification } from '../shared/Notifications';
import BatchCodeCorrectionForm from './BatchCodeCorrectionForm';
import '../../../styles/components/correction-panel.css';

const TABS = {
  REFERENCE: 'reference',
  BATCH_CODE: 'batch-code',
};

export default function CorrectionPanel({ onBack }) {
  const [activeTab, setActiveTab] = useState(TABS.REFERENCE);
  const [banner, notify, clearBanner] = useNotification();

  return (
    <section className="correction-panel">

      {/* {onBack && (
        <button
          type="button"
          className="correction-panel__back"
          onClick={onBack}
        >
          ← Back to Client Workflow
        </button>
      )} */}

      <div className="bulk-workflow__card">

        <h2 className="bulk-workflow__card-title">
          Correct an entry
        </h2>

        <p className="correction-panel__subtitle">
          Correct an existing record without recreating it.
        </p>

        <div className="correction-panel__tabs">
          <button
            type="button"
            className={`correction-panel__tab ${
              activeTab === TABS.REFERENCE
                ? 'correction-panel__tab--active'
                : ''
            }`}
            onClick={() => {
              setActiveTab(TABS.REFERENCE);
              clearBanner();
            }}
          >
            Reference entry
          </button>

          <button
            type="button"
            className={`correction-panel__tab ${
              activeTab === TABS.BATCH_CODE
                ? 'correction-panel__tab--active'
                : ''
            }`}
            onClick={() => {
              setActiveTab(TABS.BATCH_CODE);
              clearBanner();
            }}
          >
            Batch code
          </button>
        </div>

        <Notification state={banner} />

        {activeTab === TABS.REFERENCE && (
          <ReferenceCorrectionForm
            notify={notify}
            clearBanner={clearBanner}
          />
        )}

        {activeTab === TABS.BATCH_CODE && (
          <BatchCodeCorrectionForm
            notify={notify}
            clearBanner={clearBanner}
          />
        )}

      </div>
    </section>
  );
}


// ---------------------------------------------------------
// Reference correction
// ---------------------------------------------------------

const RECORD_TYPES = [
  { value: 'client', label: 'Client' },
  { value: 'model', label: 'Model' },
  { value: 'version', label: 'Version' },
];

const HINTS = {
  client:
    'The client name will be updated on the existing record. All batches linked to this client will reflect the correction.',

  model:
    'The model name will be updated across all its version records. Linked batches will reflect the corrected model name.',

  version:
    'The selected version will be updated. All batches linked to this version will reflect the correction.',
};

function ReferenceCorrectionForm({ notify, clearBanner }) {
  const [recordType, setRecordType] = useState('client');

  const [clients, setClients] = useState([]);
  const [models, setModels] = useState([]);
  const [versions, setVersions] = useState([]);

  const [selectedModel, setSelectedModel] = useState('');
  const [selected, setSelected] = useState('');

  const [newValue, setNewValue] = useState('');
  const [reason, setReason] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const loadLists = useCallback(() => {
    getExistingClients().then(setClients).catch(() => {});
    getExistingModels().then(setModels).catch(() => {});
  }, []);

  const loadVersions = useCallback((modelName) => {
    if (!modelName) {
      setVersions([]);
      return;
    }

    getVersionsByModel(modelName)
      .then(setVersions)
      .catch(() => {});
  }, []);

  useEffect(() => {
    loadLists();
  }, [loadLists]);

  useEffect(() => {
    setSelected('');
    setNewValue('');
    setReason('');
    setVersions([]);

    if (recordType === 'version') {
      loadVersions(selectedModel);
    }
  }, [recordType, selectedModel, loadVersions]);

  const uniqueModels = [
    ...new Map(models.map((m) => [m.model, m])).values(),
  ];

  const options =
    recordType === 'client'
      ? clients.map((c) => ({
          value: c.id,
          label: c.client_name,
        }))
      : recordType === 'model'
      ? uniqueModels.map((m) => ({
          value: m.model,
          label: m.model,
        }))
      : versions.map((v) => ({
          value: v.id,
          label: v.version,
        }));

  const selectedOption = options.find(
    (opt) => String(opt.value) === String(selected)
  );

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!selected || !newValue.trim() || !reason.trim()) {
      return;
    }

    // Prevent a no-op correction.
    if (
      selectedOption &&
      selectedOption.label.trim().toLowerCase() ===
        newValue.trim().toLowerCase()
    ) {
      notify('error', 'The corrected value must differ from the current value.');
      return;
    }

    setSubmitting(true);
    clearBanner();

    try {
      if (recordType === 'client') {
        await correctClient(selected, newValue.trim(), reason.trim());
      } else if (recordType === 'model') {
        await correctModel(selected, newValue.trim(), reason.trim());
        setSelectedModel('');
      } else {
        await correctModelVersion(selected, newValue.trim(), reason.trim());
      }

      notify('success', 'Correction saved successfully.');

      setNewValue('');
      setSelected('');
      setReason('');

      loadLists();

      if (recordType === 'version') {
        loadVersions(selectedModel);
      }

    } catch (err) {
      const detail =
        err?.response?.data?.error || 'Something went wrong.';

      notify('error', detail);

    } finally {
      setSubmitting(false);
    }
  };

  const typoPrompt =
    recordType === 'client'
      ? 'Select client with the typo'
      : recordType === 'model'
      ? 'Select model with the typo'
      : 'Select version with the typo';

  return (
    <form onSubmit={handleSubmit}>

      {/* STEP 1: Identify the record */}

      <div className="correction-panel__section">

        <h3 className="correction-panel__section-title">
          1. Identify the entry
        </h3>

        <p className="correction-panel__section-description">
          Select the type of record that needs correcting.
        </p>

        <label className="correction-panel__field-label">
          Entry type
        </label>

        <div className="bulk-workflow__fields">
          <div className="bulk-workflow__field">
            <select
              value={recordType}
              onChange={(e) => {
                setRecordType(e.target.value);
                setSelectedModel('');
              }}
            >
              {RECORD_TYPES.map((type) => (
                <option key={type.value} value={type.value}>
                  {type.label}
                </option>
              ))}
            </select>
          </div>
        </div>

        {recordType === 'version' && (
          <>
            <label className="correction-panel__field-label">
              Model
            </label>

            <div className="bulk-workflow__fields">
              <div className="bulk-workflow__field">
                <select
                  value={selectedModel}
                  onChange={(e) => setSelectedModel(e.target.value)}
                >
                  <option value="">Select a model</option>

                  {uniqueModels.map((m) => (
                    <option key={m.model} value={m.model}>
                      {m.model}
                    </option>
                  ))}
                </select>
              </div>
            </div>
          </>
        )}

        <label className="correction-panel__field-label">
          {recordType === 'client'
            ? 'Existing client'
            : recordType === 'model'
            ? 'Existing model'
            : 'Existing version'}
        </label>

        <div className="bulk-workflow__fields">
          <div className="bulk-workflow__field">
            <select
              value={selected}
              onChange={(e) => {
                setSelected(e.target.value);
                setNewValue('');
              }}
              disabled={recordType === 'version' && !selectedModel}
            >
              <option value="">{typoPrompt}</option>

              {options.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>
        </div>

        {options.length === 0 && (
          <p className="correction-panel__empty">
            No records available for this selection.
          </p>
        )}

      </div>


      {/* STEP 2: Enter correction */}

      <div className="correction-panel__section">

        <h3 className="correction-panel__section-title">
          2. Enter the correction
        </h3>

        <p className="correction-panel__section-description">
          Provide the corrected value for the selected record.
        </p>

        <div className="correction-panel__comparison">

          <div className="correction-panel__comparison-item">
            <label
              className="correction-panel__field-label"
              htmlFor="correction-current-value"
            >
              Current value
            </label>

            <div className="bulk-workflow__field correction-panel__readonly">
              <input
                id="correction-current-value"
                type="text"
                value={selectedOption?.label || ''}
                placeholder="Not selected"
                readOnly
                tabIndex={-1}
              />
            </div>
          </div>

          <div className="correction-panel__comparison-item">
            <label
              className="correction-panel__field-label"
              htmlFor="correction-new-value"
            >
              Correct value
            </label>

            <div className="bulk-workflow__field">
              <input
                id="correction-new-value"
                type="text"
                placeholder="Enter corrected value"
                value={newValue}
                onChange={(e) => setNewValue(e.target.value)}
                disabled={!selected}
                required
              />
            </div>
          </div>

        </div>

      </div>


      {/* STEP 3: Reason

      <div className="correction-panel__section">

        <h3 className="correction-panel__section-title">
          3. Record the reason
        </h3>

        <p className="correction-panel__section-description">
          Explain why this record requires correction.
        </p>

        <div className="bulk-workflow__fields">
          <div className="bulk-workflow__field">
            <label
              className="correction-panel__field-label"
              htmlFor="correction-reason"
            >
              Reason for correction
            </label>

            <input
              id="correction-reason"
              type="text"
              placeholder="e.g. Incorrect spelling during data entry"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              required
            />
          </div>
        </div>

      </div> */}


      {/* IMPACT */}

      <div className="correction-panel__impact">

        <span className="correction-panel__impact-icon">
          ⓘ
        </span>

        <div>
          <p className="correction-panel__impact-title">
            Impact of correction
          </p>

          <p className="correction-panel__impact-text">
            {HINTS[recordType]}
          </p>
        </div>

      </div>


      {/* ACTION */}

      <div className="bulk-workflow__actions">
        <button
          type="submit"
          className="bulk-workflow__btn bulk-workflow__btn--primary"
          disabled={
            submitting ||
            !selected ||
            !newValue.trim() ||
            !reason.trim() ||
            !selectedOption
          }
        >
          {submitting ? 'Saving…' : 'Save correction'}
        </button>
      </div>

    </form>
  );
}