import { useState, useEffect } from "react";
import { getCompany, setCompany, getExistingClients } from "../../services/ClientApi";
import "../../styles/components/CompanySetUp.css";
// Shows a one-time setup card until the company is chosen, then a quiet chip.
// refreshKey: change it (e.g. when new clients are saved) to reload the client list.
export default function CompanySetup({ refreshKey }) {
  const [company, setCompanyState] = useState(null); // { is_set, client }
  const [clients, setClients] = useState([]);
  const [selected, setSelected] = useState("");
  const [confirming, setConfirming] = useState(false);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState(null);

  useEffect(() => {
    Promise.all([getCompany(), getExistingClients()])
      .then(([c, list]) => {
        setCompanyState(c);
        setClients(list);
      })
      .catch(() => setNotice({ type: "error", message: "Couldn't load company details." }));
  }, [refreshKey]);

  const handleConfirm = async () => {
    setBusy(true);
    setNotice(null);
    try {
      const res = await setCompany(Number(selected));
      setCompanyState({ is_set: res.is_set, client: res.client });
      setConfirming(false);
    } catch (error) {
      const data = error.response?.data;
      setNotice({
        type: "error",
        message: data?.error || (data?.client && [].concat(data.client)[0]) || "Failed to set company.",
      });
      setConfirming(false);
    } finally {
      setBusy(false);
    }
  };

  if (!company) return notice ? <div className="bulk-workflow__notification bulk-workflow__notification--error">{notice.message}</div> : null;

  if (company.is_set) {
    return <div className="company-chip">Servicing company: <strong>{company.client.client_name}</strong></div>;
  }

  const chosen = clients.find((c) => String(c.id) === selected);

  return (
    <div className="bulk-workflow__card company-setup">
      <h2 className="bulk-workflow__card-title">Set up your company</h2>
      <p className="company-setup__text">
        Choose which client is your own company. This is done once and decides which devices can be rented out.
        Add the company as a client first if it isn't in the list.
      </p>

      <div className="bulk-workflow__fields">
        <div className="bulk-workflow__field">
          <span className="bulk-workflow__field-label">Company</span>
          <select value={selected} onChange={(e) => { setSelected(e.target.value); setConfirming(false); }}>
            <option value="">Select client</option>
            {clients.map((c) => <option key={c.id} value={c.id}>{c.client_name}</option>)}
          </select>
        </div>
      </div>

      {!confirming ? (
        <div className="bulk-workflow__actions">
          <button type="button" className="bulk-workflow__btn bulk-workflow__btn--primary" disabled={!selected} onClick={() => setConfirming(true)}>
            Set as company
          </button>
        </div>
      ) : (
        <div className="company-setup__confirm">
          <span>Set <strong>{chosen?.client_name}</strong> as the company? This can't be changed afterwards.</span>
          <div className="bulk-workflow__actions" style={{ marginTop: 0 }}>
            <button type="button" className="bulk-workflow__btn bulk-workflow__btn--secondary" onClick={() => setConfirming(false)} disabled={busy}>Cancel</button>
            <button type="button" className="bulk-workflow__btn bulk-workflow__btn--primary" onClick={handleConfirm} disabled={busy}>
              {busy ? "Saving…" : "Yes, set it"}
            </button>
          </div>
        </div>
      )}

      {notice && (
        <div className={`bulk-workflow__notification bulk-workflow__notification--${notice.type}`} style={{ marginTop: "1rem", marginBottom: 0 }}>
          {notice.message}
        </div>
      )}
    </div>
  );
}