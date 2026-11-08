import { useEffect, useRef, useState } from "react";

const TRANSITION_DURATION = 450;

export default function TransitionPanel({ active, children }) {
  const hasMounted = useRef(active);

  const [mounted, setMounted] = useState(active);
  const [phase, setPhase] = useState(
    active ? "entering" : "hidden"
  );

  useEffect(() => {
    let timer;

    if (active) {
      if (!hasMounted.current) {
        hasMounted.current = true;
        setMounted(true);
      }

      setPhase("entering");

      timer = setTimeout(() => {
        setPhase("visible");
      }, TRANSITION_DURATION);
    } else if (hasMounted.current) {
      setPhase("exiting");

      timer = setTimeout(() => {
        setPhase("hidden");
      }, TRANSITION_DURATION);
    }

    return () => clearTimeout(timer);
  }, [active]);

  if (!mounted) return null;

  return (
    <div
      className={`workflow-transition workflow-transition--${phase}`}
      aria-hidden={!active}
      inert={!active}
    >
      {children}
    </div>
  );
}