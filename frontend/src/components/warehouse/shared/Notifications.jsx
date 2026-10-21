import { useState, useRef, useCallback, useEffect } from "react";

// Returns [notification, notify, clear].
// notify(type, message) shows a message and hides it after `duration` ms.
export function useNotification(duration = 5000) {
  const [notification, setNotification] = useState(null);
  const timer = useRef(null);

  const clear = useCallback(() => {
    clearTimeout(timer.current);
    setNotification(null);
  }, []);

  const notify = useCallback(
    (type, message) => {
      clearTimeout(timer.current);
      setNotification({ type, message });
      timer.current = setTimeout(() => setNotification(null), duration);
    },
    [duration]
  );

  useEffect(() => () => clearTimeout(timer.current), []);

  return [notification, notify, clear];
}

export default function Notification({ state }) {
  if (!state) return null;
  return (
    <div
      role={state.type === "error" ? "alert" : "status"}
      style={{
        display: "inline-block",
        marginTop: "0.5rem",
        padding: "0.4rem 0.875rem",
        borderRadius: "4px",
        fontSize: "0.8rem",
        fontWeight: 500,
        backgroundColor: state.type === "success" ? "#16a34a" : "#dc2626",
        color: "#ffffff",
      }}
    >
      {state.message}
    </div>
  );
}