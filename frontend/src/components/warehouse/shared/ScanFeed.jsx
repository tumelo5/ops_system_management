import { useState, useRef } from "react";

// Shared state for a scanned-devices list. Entries are "ok" or "flagged".
// While any entry is flagged, the panel locks scanning until it is removed.
export function useScanEntries() {
  const [entries, setEntries] = useState([]);
  const nextId = useRef(1);

  const add = (entry) =>
    setEntries((prev) => [...prev, { id: nextId.current++, status: "ok", ...entry }]);
  const remove = (id) => setEntries((prev) => prev.filter((e) => e.id !== id));
  const flag = (id, message) =>
    setEntries((prev) => prev.map((e) => (e.id === id ? { ...e, status: "flagged", message } : e)));
  const clear = () => setEntries([]);
  const has = (sn) => entries.some((e) => e.serial_number.toLowerCase() === sn.toLowerCase());
  const hasFlagged = entries.some((e) => e.status === "flagged");

  return { entries, add, remove, flag, clear, has, hasFlagged };
}

// Backend errors: {error}, {detail}, or a serializer dict of field -> [messages]
export const messageOf = (data, fallback) => {
  if (!data) return fallback;
  if (typeof data === "string") return data;
  if (data.error) return data.error;
  if (data.detail) return data.detail;
  const first = Object.values(data)[0];
  if (Array.isArray(first)) return first[0] || fallback;
  return typeof first === "string" ? first : fallback;
};

export default function ScanFeed({ entries, onRemove }) {
  if (!entries.length) return <p className="scan-feed__empty">No devices scanned yet.</p>;
  return (
    <ul className="scan-feed">
      {entries.map((e) => (
        <li key={e.id} className={`scan-entry scan-entry--${e.status}`}>
          <span className="scan-entry__icon" aria-hidden="true">{e.status === "ok" ? "✓" : "!"}</span>
          <div className="scan-entry__body">
            <div className="scan-entry__head">
              <strong>{e.serial_number}</strong>
              {e.tag && <span className="scan-entry__tag">{e.tag}</span>}
            </div>
            {e.status === "ok" && e.meta && <div className="scan-entry__meta">{e.meta}</div>}
            {e.status === "flagged" && <div className="scan-entry__message">{e.message}</div>}
          </div>
          <button type="button" className="scan-entry__remove" onClick={() => onRemove(e.id)}>
            Remove
          </button>
        </li>
      ))}
    </ul>
  );
}