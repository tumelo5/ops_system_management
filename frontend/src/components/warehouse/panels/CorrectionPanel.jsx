import React, { useState, useEffect } from 'react';
import {
  getExistingClients,
  getExistingModels,
  getVersionsByModel,
} from '../../../services/ClientApi';
import {
  correctClient,
  correctModel,
  correctModelVersion,
  submitReassignmentRequest,
  getBatchByCode,
} from '../../../services/CorrectionApi';
import Notification, { useNotification } from '../shared/Notifications';
import '../../../styles/components/correction-panel.css';

/**
 * CorrectionPanel
 *
 * Two distinct, unrelated operations:
 * - "Fix a new entry": edit a Client/Model/Version's value directly (same PK,
 *   nothing else changes). Always self-service — pre-link or post-link, it
 *   doesn't matter, since correcting a spelling never changes identity.
 * - "Reassign batch": a client's contract ends and the batch's devices move to
 *   a different client. Creates a new Batch under the new client; the original
 *   batch and old client are left untouched, preserving history.
 */

const TABS = {
  REFERENCE: 'reference',
  BATCH: 'batch',
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
          Fix a typo in a client, model, or version — or reassign a batch to a different client.
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
            className={`correction-panel__tab ${activeTab === TABS.BATCH ? 'correction-panel__tab--active' : ''}`}
            onClick={() => { setActiveTab(TABS.BATCH); clearBanner(); }}
          >
            Reassign batch
          </button>
        </div>

        <Notification state={banner} />

        {activeTab === TABS.REFERENCE ? (
          <ReferenceCorrectionForm notify={notify} clearBanner={clearBanner} />
        ) : (
          <BatchReassignmentForm notify={notify} clearBanner={clearBanner} />
        )}
      </div>
    </section>
  );
}

// ---------------------------------------------------------------------------
// Fix a new entry (Client / Model / Version) — always direct, no gating
// ---------------------------------------------------------------------------

const RECORD_TYPES = [
  { value: 'client', label: 'Client' },
  { value: 'model', label: 'Model' },
  { value: 'version', label: 'Version' },
];

function ReferenceCorrectionForm({ notify, clearBanner }) {
  const [recordType, setRecordType] = useState('client');
  const [clients, setClients] = useState([]);
  const [models, setModels] = useState([]);
  const [versions, setVersions] = useState([]);
  const [selectedModelId, setSelectedModelId] = useState('');
  const [selectedId, setSelectedId] = useState('');
  const [newValue, setNewValue] = useState('');
  const [reason, setReason] = useState('');
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    getExistingClients().then((data) => setClients(data)).catch(() => {});
    getExistingModels().then((data) => setModels(data)).catch(() => {});
  }, []);

  useEffect(() => {
    setSelectedId('');
    setVersions([]);
    if (recordType === 'version' && selectedModelId) {
      getVersionsByModel(selectedModelId)
        .then((data) => setVersions(data))
        .catch(() => {});
    }
  }, [recordType, selectedModelId]);

  const currentOptions =
    recordType === 'client' ? clients : recordType === 'model' ? models : versions;

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!selectedId || !newValue.trim() || !reason.trim()) return;

    setSubmitting(true);
    clearBanner();

    try {
      if (recordType === 'client') {
        await correctClient(selectedId, newValue.trim(), reason.trim());
      } else if (recordType === 'model') {
        await correctModel(selectedId, newValue.trim(), reason.trim());
      } else {
        await correctModelVersion(selectedId, newValue.trim(), reason.trim());
      }
      notify('success', 'Updated successfully.');
      setNewValue('');
      setSelectedId('');
      setReason('');
    } catch (err) {
      const detail = err?.response?.data?.error || 'Something went wrong.';
      notify('error', detail);
    } finally {
      setSubmitting(false);
    }
  };

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
            <select value={selectedModelId} onChange={(e) => setSelectedModelId(e.target.value)}>
              <option value="">Select a model</option>
              {models.map((m) => (
                <option key={m.id} value={m.id}>{m.model_name}</option>
              ))}
            </select>
          </div>
        </div>
      )}

      <div className="bulk-workflow__fields">
        <div className="bulk-workflow__field">
          <select
            value={selectedId}
            onChange={(e) => setSelectedId(e.target.value)}
            disabled={recordType === 'version' && !selectedModelId}
          >
            <option value="">
              {recordType === 'client' ? 'Select client with the typo'
                : recordType === 'model' ? 'Select model with the typo'
                : 'Select version with the typo'}
            </option>
            {currentOptions.map((opt) => (
              <option key={opt.id} value={opt.id}>
                {opt.client_name || opt.model_name || opt.version}
              </option>
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
          disabled={submitting || !selectedId || !newValue.trim() || !reason.trim()}
        >
          {submitting ? 'Saving…' : 'Save correction'}
        </button>
      </div>

      <p className="correction-panel__hint">
        This updates the value directly — every batch already linked to this entry
        will reflect the correction automatically.
      </p>
    </form>
  );
}

// ---------------------------------------------------------------------------
// Reassign batch — client-only, creates a new Batch under the new client
// ---------------------------------------------------------------------------

function BatchReassignmentForm({ notify, clearBanner }) {
  const [batchCode, setBatchCode] = useState('');
  const [batch, setBatch] = useState(null);
  const [lookingUp, setLookingUp] = useState(false);

  const [clients, setClients] = useState([]);
  const [newClientId, setNewClientId] = useState('');
  const [newBatchCode, setNewBatchCode] = useState('');
  const [reason, setReason] = useState('');
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    getExistingClients().then((data) => setClients(data)).catch(() => {});
  }, []);

  const handleLookup = async (e) => {
    e.preventDefault();
    if (!batchCode.trim()) return;

    setLookingUp(true);
    clearBanner();
    setBatch(null);

    try {
      const data = await getBatchByCode(batchCode.trim());
      const found = Array.isArray(data) ? data[0] : data;
      if (!found) {
        notify('error', `No batch found with code "${batchCode}".`);
      } else {
        setBatch(found);
      }
    } catch (err) {
      notify('error', 'Could not look up that batch.');
    } finally {
      setLookingUp(false);
    }
  };

  const handleReassign = async (e) => {
    e.preventDefault();
    if (!batch || !newClientId || !newBatchCode.trim() || !reason.trim()) return;

    setSubmitting(true);
    clearBanner();

    try {
      await submitReassignmentRequest(batch.id, {
        clientId: newClientId,
        batchCode: newBatchCode.trim(),
        reason: reason.trim(),
      });
      notify('success', 'Reassignment request submitted — awaiting Finance approval.');
      setBatch(null);
      setBatchCode('');
      setNewClientId('');
      setNewBatchCode('');
      setReason('');
    } catch (err) {
      const detail = err?.response?.data?.error || 'Something went wrong.';
      notify('error', detail);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div>
      <form className="bulk-workflow__fields" onSubmit={handleLookup} style={{ alignItems: 'flex-start' }}>
        <div className="bulk-workflow__field">
          <input
            placeholder="Enter the batch code"
            value={batchCode}
            onChange={(e) => setBatchCode(e.target.value)}
          />
        </div>
        <div className="bulk-workflow__actions" style={{ marginTop: 0 }}>
          <button
            type="submit"
            className="bulk-workflow__btn"
            disabled={lookingUp || !batchCode.trim()}
          >
            {lookingUp ? 'Looking up…' : 'Find batch'}
          </button>
        </div>
      </form>

      {batch && (
        <form onSubmit={handleReassign}>
          <div className="correction-panel__current">
            <span className="correction-panel__current-label">Currently on file</span>
            <span className="correction-panel__current-value">
              {batch.client_name} — {batch.model_name} {batch.version}
            </span>
          </div>

          <div className="bulk-workflow__fields">
            <div className="bulk-workflow__field">
              <select value={newClientId} onChange={(e) => setNewClientId(e.target.value)}>
                <option value="">Select new client</option>
                {clients.map((c) => (
                  <option key={c.id} value={c.id}>{c.client_name}</option>
                ))}
              </select>
            </div>
            <div className="bulk-workflow__field">
              <input
                placeholder="New batch code"
                value={newBatchCode}
                onChange={(e) => setNewBatchCode(e.target.value)}
              />
            </div>
          </div>

          <div className="bulk-workflow__fields">
            <div className="bulk-workflow__field">
              <input
                placeholder="Reason for reassignment"
                value={reason}
                onChange={(e) => setReason(e.target.value)}
              />
            </div>
          </div>

          <div className="bulk-workflow__actions">
            <button
              type="submit"
              className="bulk-workflow__btn bulk-workflow__btn--primary"
              disabled={submitting || !newClientId || !newBatchCode.trim() || !reason.trim()}
            >
              {submitting ? 'Saving…' : 'Reassign batch'}
            </button>
          </div>

          <p className="correction-panel__hint">
            This creates a new batch under the selected client and moves this batch's
            devices to it. The original batch and client stay exactly as they were.
          </p>
        </form>
      )}
    </div>
  );
}