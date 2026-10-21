import { useState } from "react";
import { getActiveRental, endRentals } from "../../../services/ClientApi";
import ScanBox, { useScanBox, messageOf } from "../shared/ScanBox";
import "../../../styles/components/EndRentalPanel.css";

const MAX_DEVICES = 50;
const pad = (n) => String(n).padStart(2, "0");
const toDateInput = (d) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
const fmtDate = (iso) => (iso ? new Date(iso).toLocaleDateString() : "—");

export default function EndRentalPanel() {
  const [endDate, setEndDate] = useState(toDateInput(new Date()));
  const [submitting, setSubmitting] = useState(false);
  const [notice, setNotice] = useState(null);

  const box = useScanBox({
    max: MAX_DEVICES,
    validate: async (sn) => {
      const r = await getActiveRental(sn);
      const past = r.expected_return_date && new Date(r.expected_return_date) < new Date();
      return {
        meta: `${r.client} · started ${fmtDate(r.start_date)}${past ? " · past expected return" : ""}`,
        data: {
          serial_number: r.serial_number || sn,
          rental_id: r.rental_id,
          start_date: r.start_date,
        },
      };
    },
  });

  const n = box.items.length;
  const today = toDateInput(new Date());
  // The end date can't be before any rental's start, so use the latest start in the batch
  const minDate = box.items
    .filter((it) => it.start_date)
    .map((it) => toDateInput(new Date(it.start_date)))
    .sort()
    .pop();
  const dateOk = endDate && endDate <= today && (!minDate || endDate >= minDate);
  const canEnd = n > 0 && !box.blocked && !submitting && dateOk;

  const handleEnd = async () => {
    setSubmitting(true);
    setNotice(null);
    try {
      const res = await endRentals({
        end_date: endDate,
        rental_ids: box.items.map((it) => it.rental_id),
      });
      box.clear();
      setNotice({ type: "success", message: res.message });
    } catch (error) {
      // All-or-nothing: nothing was ended, so the lines stay as they are
      setNotice({ type: "error", message: messageOf(error.response?.data, "Failed to end rentals.") });
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <section className="bulk-workflow__section">
      <div className="bulk-workflow__card">
        <h2 className="bulk-workflow__card-title">Scan returned devices</h2>
        <ScanBox box={box} max={MAX_DEVICES} />
      </div>

      <div className="bulk-workflow__card">
        <h2 className="bulk-workflow__card-title">End date</h2>
        <div className="bulk-workflow__fields">
          <div className="bulk-workflow__field">
            <span className="bulk-workflow__field-label">Rental end date (all devices)</span>
            <input
              type="date"
              value={endDate}
              min={minDate}
              max={today}
              onChange={(e) => setEndDate(e.target.value)}
            />
          </div>
        </div>
        {minDate && endDate && endDate < minDate && (
          <p className="scan-lock-hint">The end date can't be before {minDate}, the latest start date in this batch.</p>
        )}

        {notice && (
          <div
            className={`bulk-workflow__notification bulk-workflow__notification--${notice.type}`}
            style={{ margin: "1rem 0 0" }}
          >
            {notice.message}
          </div>
        )}

        <div className="bulk-workflow__actions" style={{ justifyContent: "flex-end", marginTop: "1.25rem" }}>
          <button type="button" className="bulk-workflow__btn bulk-workflow__btn--primary" onClick={handleEnd} disabled={!canEnd}>
            {submitting ? "Ending…" : `End ${n || ""} rental${n === 1 ? "" : "s"}`}
          </button>
        </div>
      </div>
    </section>
  );
}