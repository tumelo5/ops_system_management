import React, { useState, useEffect, useCallback } from 'react';
import {
  getExistingClients,
  getExistingModels,
  getVersionsByModel,
} from '../../../services/ClientApi';
import {
  correctClient,
  correctModel,
  correctModelVersion,
} from '../../../services/CorrectionApi';
import Notification, { useNotification } from '../shared/Notifications';
import BatchCodeCorrectionForm from './BatchCodeCorrectionForm';
import '../../../styles/components/correction-panel.css';

/**
 * CorrectionPanel
 *
 * Two kinds of typo correction:
 * - "Fix a new entry": edit a Client/Model/Version's value directly (same PK,
 *   nothing else changes). Always self-service — pre-link or post-link, it
 *   doesn't matter, since correcting a spelling never changes identity.
 * - "Fix a batch code": correct a mistyped batch code, only while no device has
 *   been scanned or registered under it (see BatchCodeCorrectionForm).
 */

const TABS = {
  REFERENCE: 'reference',
  BATCH_CODE: 'batch-code',
};

export default function CorrectionPanel({ onBack }) {
  const [activeTab, setActiveTab] = useState(TABS.REFERENCE);
  const [banner, notify, clearBanner] = useNotification();

  return (
    <section className="correction-panel">
      {onBack && (
        <button type="button" className="correction-panel__back" onClick={onBack}>
          ← Back to Client Workflow
        </button>
      )}

      <div className="bulk-workflow__card">
        <h2 className="bulk-workflow__card-title">Correct an entry</h2>
        <p className="correction-panel__subtitle">
          Fix a typo in a client, model, version, or batch code.
        </p>

        <div className="correction-panel__tabs">
          <button
            type="button"
            className={`correction-panel__tab ${activeTab === TABS.REFERENCE ? 'correction-panel__tab--active' : ''}`}
            onClick={() => { setActiveTab(TABS.REFERENCE); clearBanner(); }}
          >
            Fix a new entry
          </button>
          <button
            type="button"
            className={`correction-panel__tab ${activeTab === TABS.BATCH_CODE ? 'correction-panel__tab--active' : ''}`}
            onClick={() => { setActiveTab(TABS.BATCH_CODE); clearBanner(); }}
          >
            Fix a batch code
          </button>
        </div>

        <Notification state={banner} />

        {activeTab === TABS.REFERENCE && (
          <ReferenceCorrectionForm notify={notify} clearBanner={clearBanner} />
        )}
        {activeTab === TABS.BATCH_CODE && (
          <BatchCodeCorrectionForm notify={notify} clearBanner={clearBanner} />
        )}
      </div>
    </section>
  );
}

// ---------------------------------------------------------------------------
// Fix a new entry (Client / Model / Version) — always direct, no gating
//
// Model and version are one table: a "model" is a model name shared by one or
// more version rows. So:
//   - Client:  picked by id, renamed on its own
//   - Model:   picked by NAME, renamed on every version row of that model
//   - Version: pick the model name first, then pick one version row by id
// ---------------------------------------------------------------------------

const RECORD_TYPES = [
  { value: 'client', label: 'Client' },
  { value: 'model', label: 'Model' },
  { value: 'version', label: 'Version' },
];

const HINTS = {
  client: 'This updates the client name directly. Every batch linked to this client reflects the correction.',
  model: 'This renames the model on all of its versions. Every batch linked to them reflects the correction.',
  version: 'This updates the version directly. Every batch linked to it reflects the correction.',
};

function ReferenceCorrectionForm({ notify, clearBanner }) {
  const [recordType, setRecordType] = useState('client');
  const [clients, setClients] = useState([]); // [{ id, client_name }]
  const [models, setModels] = useState([]); // [{ model }]  distinct model names
  const [versions, setVersions] = useState([]); // [{ id, version }]  of the model chosen below
  const [selectedModel, setSelectedModel] = useState(''); // model name, used on the Version tab
  const [selected, setSelected] = useState(''); // client id, model name or version id, by tab
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
    getVersionsByModel(modelName).then(setVersions).catch(() => {});
  }, []);

  useEffect(() => {
    loadLists();
  }, [loadLists]);

  // Changing the tab or the chosen model clears the selection and loads that model's versions
  useEffect(() => {
    setSelected('');
    setVersions([]);
    if (recordType === 'version') loadVersions(selectedModel);
  }, [recordType, selectedModel, loadVersions]);

  // One shape for every tab: { value, label }. Model names are de-duplicated defensively.
  const uniqueModels = [...new Map(models.map((m) => [m.model, m])).values()];
  const options =
    recordType === 'client'
      ? clients.map((c) => ({ value: c.id, label: c.client_name }))
      : recordType === 'model'
      ? uniqueModels.map((m) => ({ value: m.model, label: m.model }))
      : versions.map((v) => ({ value: v.id, label: v.version }));

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!selected || !newValue.trim() || !reason.trim()) return;

    setSubmitting(true);
    clearBanner();

    try {
      if (recordType === 'client') {
        await correctClient(selected, newValue.trim(), reason.trim());
      } else if (recordType === 'model') {
        await correctModel(selected, newValue.trim(), reason.trim());
        setSelectedModel(''); // the old name no longer exists
      } else {
        await correctModelVersion(selected, newValue.trim(), reason.trim());
      }
      notify('success', 'Updated successfully.');
      setNewValue('');
      setSelected('');
      setReason('');
      loadLists(); // every screen reads these lists, so refresh them
      if (recordType === 'version') loadVersions(selectedModel);
    } catch (err) {
      const detail = err?.response?.data?.error || 'Something went wrong.';
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
      <div className="bulk-workflow__fields">
        <div className="bulk-workflow__field">
          <select value={recordType} onChange={(e) => setRecordType(e.target.value)}>
            {RECORD_TYPES.map((t) => (
              <option key={t.value} value={t.value}>{t.label}</option>
            ))}
          </select>
        </div>
      </div>

      {recordType === 'version' && (
        <div className="bulk-workflow__fields">
          <div className="bulk-workflow__field">
            <select value={selectedModel} onChange={(e) => setSelectedModel(e.target.value)}>
              <option value="">Select a model</option>
              {uniqueModels.map((m) => (
                <option key={m.model} value={m.model}>{m.model}</option>
              ))}
            </select>
          </div>
        </div>
      )}

      <div className="bulk-workflow__fields">
        <div className="bulk-workflow__field">
          <select
            value={selected}
            onChange={(e) => setSelected(e.target.value)}
            disabled={recordType === 'version' && !selectedModel}
          >
            <option value="">{typoPrompt}</option>
            {options.map((opt) => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>
        </div>
        <div className="bulk-workflow__field">
          <input
            placeholder="Correct value"
            value={newValue}
            onChange={(e) => setNewValue(e.target.value)}
          />
        </div>
      </div>

      <div className="bulk-workflow__fields">
        <div className="bulk-workflow__field">
          <input
            placeholder="Reason for this correction"
            value={reason}
            onChange={(e) => setReason(e.target.value)}
          />
        </div>
      </div>

      <div className="bulk-workflow__actions">
        <button
          type="submit"
          className="bulk-workflow__btn bulk-workflow__btn--primary"
          disabled={submitting || !selected || !newValue.trim() || !reason.trim()}
        >
          {submitting ? 'Saving…' : 'Save correction'}
        </button>
      </div>

      <p className="correction-panel__hint">{HINTS[recordType]}</p>
    </form>
  );
}