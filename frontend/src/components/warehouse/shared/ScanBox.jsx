import { useState, useRef, useMemo, useEffect } from "react";
import "../../../styles/components/ScanBox.css";

const MIN_LINES = 3;   // visible lines when the box is empty
const MAX_LINES = 10;  // after this, the box scrolls inside

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

/**
 * One text box, one serial number per line. Scanners send "serial + Enter", so each
 * scan becomes a new line. Everything (rows, errors, lock) is derived from the text:
 * delete a red line and the problem, and the lock, disappear with it.
 *
 * validate(sn) -> resolves { meta, data } when the SN is fine, throws when it is not.
 */
export function useScanBox({ validate, max = 50 }) {
  const [text, setText] = useState("");
  const [results, setResults] = useState({}); // lower-cased SN -> {status, meta, data, message, tag, redundant}
  const [checking, setChecking] = useState(false);
  const [notice, setNotice] = useState(null);
  const inputRef = useRef(null);
  const timer = useRef(null);

  const say = (message) => {
    setNotice(message);
    clearTimeout(timer.current);
    timer.current = setTimeout(() => setNotice(null), 4000);
  };

  // The last line is the one being typed/scanned
  const lines = useMemo(() => text.split("\n"), [text]);

  const rows = useMemo(() => {
    const seen = new Set();
    return lines.slice(0, -1).map((raw) => {
      const sn = raw.trim();
      if (!sn) return { sn, status: "empty" };
      const key = sn.toLowerCase();
      if (seen.has(key)) {
        return { sn, status: "flagged", tag: "Duplicate", message: "Already scanned in this batch.", redundant: true };
      }
      seen.add(key);
      const r = results[key];
      if (!r) {
        return { sn, status: "flagged", tag: "Edited", message: "This line was edited. Remove it and scan again." };
      }
      return { sn, ...r };
    });
  }, [lines, results]);

  const items = rows
    .filter((r) => r.status === "ok")
    .map((r) => ({ serial_number: r.sn, meta: r.meta, ...r.data }));
  const problems = rows
    .map((r, i) => ({ ...r, line: i + 1 }))
    .filter((r) => r.status === "flagged");
  const blocked = checking || problems.length > 0;

  // Keep the cursor on the live line whenever scanning is allowed
  useEffect(() => {
    const ta = inputRef.current;
    if (!ta || blocked) return;
    ta.focus();
    ta.setSelectionRange(ta.value.length, ta.value.length);
    ta.scrollTop = ta.scrollHeight;
  }, [rows.length, blocked]);

  const commit = async () => {
    if (checking) return;
    if (problems.length > 0) {
      say("Remove the red serial number first, then keep scanning.");
      return;
    }
    const sn = lines[lines.length - 1].trim();
    if (!sn) return;
    const counted = rows.filter((r) => r.status !== "empty").length;
    if (counted >= max) {
      say(`A batch can hold at most ${max} devices.`);
      return;
    }

    const key = sn.toLowerCase();
    const isDuplicate = rows.some((r) => r.status !== "empty" && r.sn.toLowerCase() === key);
    setText([...lines.slice(0, -1), sn, ""].join("\n"));
    if (isDuplicate) {
      say(`${sn} is already in this batch.`);
      return;
    }

    setChecking(true);
    setResults((r) => ({ ...r, [key]: { status: "checking" } }));
    try {
      const out = await validate(sn);
      setResults((r) => ({ ...r, [key]: { status: "ok", meta: out?.meta, data: out?.data } }));
    } catch (error) {
      const message = messageOf(error.response?.data, "Couldn't check this device.");
      const notFound = error.response?.status === 404;
      // A plain "not found" message only repeats the tag, so the detail list skips it
      const redundant = notFound && /not found/i.test(message);
      setResults((r) => ({
        ...r,
        [key]: { status: "flagged", message, tag: notFound ? "Not found" : "Rejected", redundant },
      }));
    } finally {
      setChecking(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.ctrlKey || e.metaKey) {
      if (e.key.toLowerCase() === "v") e.preventDefault(); // no paste
      return; // allow select all, copy, cut, undo
    }
    if (e.key === "Enter") {
      e.preventDefault();
      commit();
      return;
    }
    if (e.key.length > 1) return; // Backspace, Delete, arrows, Home/End ...
    // A typed character: only on the live line, and only while scanning is allowed
    const ta = e.target;
    const liveLineStart = ta.value.lastIndexOf("\n") + 1;
    if (blocked || ta.selectionStart < liveLineStart) e.preventDefault();
  };

  const handlePaste = (e) => {
    e.preventDefault();
    say("Pasting isn't supported. Scan or type one serial number at a time.");
  };

  const flag = (sn, message, tag = "Rejected") =>
    setResults((r) => ({ ...r, [sn.toLowerCase()]: { status: "flagged", message, tag } }));

  const clear = () => {
    setText("");
    setResults({});
    setNotice(null);
  };

  return {
    text, lines, rows, items, problems, blocked, notice,
    inputRef, handleKeyDown, handlePaste, flag, clear,
    handleChange: (e) => setText(e.target.value),
  };
}

export default function ScanBox({ box, max = 50, placeholder = "Scan a serial number, one per line" }) {
  const backdropRef = useRef(null);
  const syncScroll = (e) => {
    if (backdropRef.current) backdropRef.current.scrollTop = e.target.scrollTop;
  };

  const visible = Math.min(Math.max(box.lines.length, MIN_LINES), MAX_LINES);
  const longest = box.lines.reduce((m, l) => Math.max(m, l.length), 0); // drives the width in ScanBox.css
  const details = box.problems.filter((p) => !p.redundant); // problems the tag doesn't already explain

  return (
    <div className="scan-box-wrap" style={{ "--scan-chars": longest }}>
      <div className="scan-box__header">
        <span>{box.items.length} / {max} devices</span>
      </div>

      <div className={`scan-box${box.blocked ? " scan-box--locked" : ""}`} style={{ height: `calc(${visible} * 1.75rem + 1.2rem + 2px)` }}>
        {/* Behind the text: the coloured bars and the right-hand labels */}
        <div className="scan-box__backdrop" ref={backdropRef} aria-hidden="true">
          {box.lines.map((line, i) => {
            const row = box.rows[i];
            const status = row ? row.status : "live";
            const label =
              status === "checking" ? "Checking…" :
              status === "flagged" ? row.tag :
              status === "ok" ? row.meta : "";
            return (
              <div key={i} className={`scan-box__line scan-box__line--${status}`}>
                <span className="scan-box__sn">{line || "\u00a0"}</span>
                {label && (
                  <span className="scan-box__meta" title={status === "flagged" ? row.message : undefined}>
                    {label}
                  </span>
                )}
              </div>
            );
          })}
        </div>

        <textarea
          ref={box.inputRef}
          className="scan-box__input"
          value={box.text}
          onChange={box.handleChange}
          onKeyDown={box.handleKeyDown}
          onPaste={box.handlePaste}
          onDrop={(e) => e.preventDefault()}
          onScroll={syncScroll}
          placeholder={placeholder}
          aria-label="Scanned serial numbers"
          wrap="off"
          spellCheck={false}
          autoComplete="off"
          autoCapitalize="off"
        />
      </div>

      {box.problems.length > 0 ? (
        <>
          {details.length > 0 && (
            <ul className="scan-box__problems">
              {details.map((p) => (
                <li key={p.line}>{p.message}</li>
              ))}
            </ul>
          )}
          <p className="scan-lock-hint">Remove the flagged serial number to resume scanning.</p>
        </>
      ) : (
        box.notice && <p className="scan-box__notice">{box.notice}</p>
      )}
    </div>
  );
}