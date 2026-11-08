
import React, { useState } from 'react';
import {
  findBatchForCorrection,
  correctBatchCode,
} from '../../../services/BatchApi';

/**
 * BatchCodeCorrectionForm
 *
 * Fix a mistyped batch code.
 *
 * A batch can only be corrected while no device has been
 * scanned or registered under it.
 *
 * Self-contained: manages its own API calls and correction state.
 */

export default function BatchCodeCorrectionForm({ notify, clearBanner }) {
  const [searchCode, setSearchCode] = useState('');
  const [batch, setBatch] = useState(null);

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
    setNewCode('');
    setReason('');

    try {
      setBatch(
        await findBatchForCorrection(searchCode.trim().toLowerCase())
      );
    } catch (err) {
      notify(
        'error',
        err?.response?.data?.error || 'Could not look up that batch.'
      );
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
      await correctBatchCode(
        batch.id,
        newCode.trim(),
        reason.trim()
      );

      notify('success', 'Batch code corrected.');

      setBatch(null);
      setSearchCode('');
      setNewCode('');
      setReason('');

    } catch (err) {
      notify(
        'error',
        err?.response?.data?.error || 'Something went wrong.'
      );
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div>

      {/* Batch lookup */}

      <form
        className="bulk-workflow__fields"
        onSubmit={handleLookup}
        style={{ alignItems: 'flex-start' }}
      >
        <div className="bulk-workflow__field">
          <input
            type="text"
            placeholder="Enter the batch code with the typo"
            value={searchCode}
            onChange={(e) => setSearchCode(e.target.value)}
          />
        </div>

        <div
          className="bulk-workflow__actions"
          style={{ marginTop: 0 }}
        >
          <button
            type="submit"
            className="bulk-workflow__btn"
            disabled={lookingUp || !searchCode.trim()}
          >
            {lookingUp ? 'Looking up…' : 'Find batch'}
          </button>
        </div>
      </form>


      {/* Batch information and correction */}

      {batch && (
        <form onSubmit={handleSubmit}>

          {/* Batch details table */}

          <div className="correction-panel__batch-details">

            <h3 className="correction-panel__batch-title">
              Batch details
            </h3>

            <table className="correction-panel__batch-table">
              <tbody>

                <tr>
                  <th scope="row">Batch code</th>
                  <td>{batch.batch_code}</td>
                </tr>

                <tr>
                  <th scope="row">Client</th>
                  <td>{batch.client_name}</td>
                </tr>

                <tr>
                  <th scope="row">Device model</th>
                  <td>{batch.model}</td>
                </tr>

                <tr>
                  <th scope="row">Version</th>
                  <td>{batch.version}</td>
                </tr>

              </tbody>
            </table>

          </div>


          {/* Correction eligibility */}

          {!batch.correctable ? (

            <div className="correction-panel__batch-notice">
              <span>ⓘ</span>

              <span>
                Devices have already been scanned or registered
                under this batch code, so it cannot be corrected.
              </span>
            </div>

          ) : (

            <>

              {/* Correction input */}

              <div className="correction-panel__section">

                <h3 className="correction-panel__section-title">
                  Enter the correction
                </h3>

                <p className="correction-panel__section-description">
                  Provide the corrected batch code and explain
                  why the change is necessary.
                </p>

                <div className="bulk-workflow__fields">

                  <div className="bulk-workflow__field">
                    <label className="correction-panel__field-label">
                      Correct batch code
                    </label>

                    <input
                      type="text"
                      placeholder="Enter corrected batch code"
                      value={newCode}
                      onChange={(e) => setNewCode(e.target.value)}
                      required
                    />
                  </div>

                  <div className="bulk-workflow__field">
                    <label className="correction-panel__field-label">
                      Reason for correction
                    </label>

                    <input
                      type="text"
                      placeholder="Explain the reason for this correction"
                      value={reason}
                      onChange={(e) => setReason(e.target.value)}
                      required
                    />
                  </div>

                </div>

              </div>


              {/* Impact explanation */}

              <div className="correction-panel__impact">

                <span className="correction-panel__impact-icon">
                  ⓘ
                </span>

                <div>
                  <p className="correction-panel__impact-title">
                    Correction restriction
                  </p>

                  <p className="correction-panel__impact-text">
                    A batch code can only be corrected while no
                    device has been scanned or registered under it,
                    because serial numbers carry the batch code.
                  </p>
                </div>

              </div>


              {/* Save correction */}

              <div className="bulk-workflow__actions">

                <button
                  type="submit"
                  className="bulk-workflow__btn bulk-workflow__btn--primary"
                  disabled={
                    submitting ||
                    !newCode.trim() ||
                    !reason.trim()
                  }
                >
                  {submitting ? 'Saving…' : 'Save correction'}
                </button>

              </div>

            </>

          )}

        </form>
      )}

    </div>
  );
}
