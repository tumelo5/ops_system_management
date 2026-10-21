import { useState, useEffect } from "react";
import { getExistingClients, getCompany, checkRentable, submitRentals } from "../../../services/ClientApi";
import ScanBox, { useScanBox, messageOf } from "../shared/ScanBox";


const MAX_DEVICES = 50; // matches max_length=50 in DeviceRentalView

export default function RentalPanel() {
  const [clients, setClients] = useState([]);
  const [company, setCompany] = useState(null); // { is_set, client }
  const [clientId, setClientId] = useState("");
  const [returnDate, setReturnDate] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [notice, setNotice] = useState(null);

  const box = useScanBox({
    max: MAX_DEVICES,
    validate: async (sn) => {
      const d = await checkRentable(sn);
      return {
        meta: [d.model_name, d.version_name].filter(Boolean).join(" · "),
        data: { serial_number: d.serial_number || sn },
      };
    },
  });

  useEffect(() => {
    Promise.all([getExistingClients(), getCompany()])
      .then(([list, c]) => {
        setClients(list);
        setCompany(c);
      })
      .catch(() => setNotice({ type: "error", message: "Couldn't load clients." }));
  }, []);

  const rentableClients = clients.filter((c) => c.id !== company?.client?.id);
  const clientName = clients.find((c) => String(c.id) === clientId)?.client_name;
  const companyMissing = company && !company.is_set;
  const n = box.items.length;
  const canAssign = clientId && n > 0 && !box.blocked && !submitting && !companyMissing;

  const handleAssign = async () => {
    setSubmitting(true);
    setNotice(null);
    try {
      const payload = box.items.map((it) => ({
        device: it.serial_number,
        rental_client: Number(clientId),
        expected_return_date: returnDate ? new Date(returnDate).toISOString() : null,
      }));
      const res = await submitRentals(payload);
      box.clear();
      setNotice({ type: "success", message: res.message });
    } catch (error) {
      const data = error.response?.data;
      if (Array.isArray(data)) {
        // Per-row serializer errors line up with the order of the lines
        data.forEach((err, i) => {
          const field = err && Object.keys(err)[0];
          if (field && box.items[i]) box.flag(box.items[i].serial_number, [].concat(err[field])[0]);
        });
        setNotice({ type: "error", message: "Some devices were rejected. Remove the red lines to continue." });
      } else {
        setNotice({ type: "error", message: messageOf(data, "Failed to assign rentals.") });
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <section className="bulk-workflow__section">
      <div className="bulk-workflow__card">
        <h2 className="bulk-workflow__card-title">Rental details</h2>
        {companyMissing && (
          <div className="bulk-workflow__notification bulk-workflow__notification--error" style={{ margin: "0 0 1rem" }}>
            The company isn't set up yet. Set it in Clients &amp; Batches first.
          </div>
        )}
        <div className="bulk-workflow__fields">
          <div className="bulk-workflow__field">
            <span className="bulk-workflow__field-label">Rent to</span>
            <select value={clientId} onChange={(e) => setClientId(e.target.value)}>
              <option value="">Select client</option>
              {rentableClients.map((c) => (
                <option key={c.id} value={c.id}>{c.client_name}</option>
              ))}
            </select>
          </div>
          <div className="bulk-workflow__field">
            <span className="bulk-workflow__field-label">Expected return (all devices)</span>
            <input type="datetime-local" value={returnDate} onChange={(e) => setReturnDate(e.target.value)} />
          </div>
        </div>
      </div>

      <div className="bulk-workflow__card">
        <h2 className="bulk-workflow__card-title">Scan devices</h2>
        <ScanBox box={box} max={MAX_DEVICES} />

        {notice && (
          <div
            className={`bulk-workflow__notification bulk-workflow__notification--${notice.type}`}
            style={{ margin: "1rem 0 0" }}
          >
            {notice.message}
          </div>
        )}

        <div className="bulk-workflow__actions" style={{ justifyContent: "flex-end", marginTop: "1.25rem" }}>
          <button type="button" className="bulk-workflow__btn bulk-workflow__btn--primary" onClick={handleAssign} disabled={!canAssign}>
            {submitting
              ? "Assigning…"
              : `Assign ${n || ""} device${n === 1 ? "" : "s"}${clientName ? ` to ${clientName}` : ""}`}
          </button>
        </div>
      </div>
    </section>
  );
}