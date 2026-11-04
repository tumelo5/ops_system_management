import React, { useState } from 'react';
import { findBatchForCorrection, correctBatchCode } from '../../../services/CorrectionApi';

/**
 * BatchCodeCorrectionForm
 *
 * Fix a mistyped batch code. The batch is found by its code, and the server says whether
 * it can still be corrected: a serial number carries its batch code, so once a device has
 * been scanned or registered under a batch, its code is no longer a typo.
 *
 * Self-contained: it has its own API calls and does not depend on the reassignment feature.
 */
export default function BatchCodeCorrectionForm({ notify, clearBanner }) {
  const [searchCode, setSearchCode] = useState('');
  const [batch, setBatch] = useState(null); // { id, batch_code, client_name, model, version, correctable }
  const [lookingUp, setLookingUp] = useState(false);
  const [newCode, setNewCode] = useState('');
  const [reason, setReason] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const handleLookup = async (e) => {
    e.preventDefault();
    if (!searchCode.trim()) return;

    setLookingUp(true);
    clearBanner();
    setBatch(null);

    try {
      setBatch(await findBatchForCorrection(searchCode.trim().toLowerCase()));
    } catch (err) {
      notify('error', err?.response?.data?.error || 'Could not look up that batch.');
    } finally {
      setLookingUp(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!batch || !newCode.trim() || !reason.trim()) return;

    setSubmitting(true);
    clearBanner();

    try {
      await correctBatchCode(batch.id, newCode.trim(), reason.trim());
      notify('success', 'Batch code corrected.');
      setBatch(null);
      setSearchCode('');
      setNewCode('');
      setReason('');
    } catch (err) {
      notify('error', err?.response?.data?.error || 'Something went wrong.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div>
      <form className="bulk-workflow__fields" onSubmit={handleLookup} style={{ alignItems: 'flex-start' }}>
        <div className="bulk-workflow__field">
          <input
            placeholder="Enter the batch code with the typo"
            value={searchCode}
            onChange={(e) => setSearchCode(e.target.value)}
          />
        </div>
        <div className="bulk-workflow__actions" style={{ marginTop: 0 }}>
          <button
            type="submit"
            className="bulk-workflow__btn"
            disabled={lookingUp || !searchCode.trim()}
          >
            {lookingUp ? 'Looking up…' : 'Find batch'}
          </button>
        </div>
      </form>

      {batch && (
        <form onSubmit={handleSubmit}>
          <div className="correction-panel__current">
            <span className="correction-panel__current-label">Currently on file</span>
            <span className="correction-panel__current-value">
              {batch.batch_code} — {batch.client_name} — {batch.model} {batch.version}
            </span>
          </div>

          {!batch.correctable ? (
            <p className="correction-panel__hint">
              Devices have already been scanned or registered under this batch code, so it can't be
              corrected.
            </p>
          ) : (
            <>
              <div className="bulk-workflow__fields">
                <div className="bulk-workflow__field">
                  <input
                    placeholder="Correct batch code"
                    value={newCode}
                    onChange={(e) => setNewCode(e.target.value)}
                  />
                </div>
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
                  disabled={submitting || !newCode.trim() || !reason.trim()}
                >
                  {submitting ? 'Saving…' : 'Save correction'}
                </button>
              </div>

              <p className="correction-panel__hint">
                A batch code can only be corrected while no device has been scanned or registered
                under it, because serial numbers carry the batch code.
              </p>
            </>
          )}
        </form>
      )}
    </div>
  );
}