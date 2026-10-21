import "../../styles/components/ModelPicker.css";

const Icon = ({ children }) => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor"
       strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
    {children}
  </svg>
);

const ICONS = {
  clients: (
    <Icon>
      <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" />
      <circle cx="9" cy="7" r="4" />
      <path d="M22 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75" />
    </Icon>
  ),
  rentals: (
    <Icon>
      <rect x="3" y="4" width="18" height="16" rx="2" />
      <path d="M3 10h18M8 2v4M16 2v4" />
    </Icon>
  ),
  returns: (
    <Icon>
      <path d="M9 14 4 9l5-5" />
      <path d="M4 9h10a6 6 0 0 1 0 12h-3" />
    </Icon>
  ),
};

const GROUPS = [
  {
    id: "clients",
    label: "Clients & Batches",
    hint: "Set up clients, models and batch codes, then scan devices",
    defaultMode: "bulk_clients",
    modes: [
      { value: "bulk_clients", label: "Add Clients" },
      { value: "existing_client", label: "Existing Client" },
      { value: "correct_info", label: "Correct Info" },
    ],
  },
  {
    id: "rentals",
    label: "Rentals",
    hint: "Assign company devices to a client or end a rental",
    defaultMode: "assign_rental",
    modes: [
      { value: "assign_rental", label: "Assign Rental" },
      { value: "end_rental", label: "End Rental" },
    ],
  },
  {
    id: "returns",
    label: "Device Returning",
    hint: "Receive devices back from the field and log the return batch",
    defaultMode: "device_returning",
    modes: [{ value: "device_returning", label: "Device Returning" }],
    disabled: true,
  },
];

export default function ModePicker({ value, onChange }) {
  const activeGroup = GROUPS.find((g) => g.modes.some((m) => m.value === value));
  const showTabs = activeGroup && activeGroup.modes.length > 1;

  return (
    <div className="mode-picker-wrap">
      <div className="mode-picker" role="radiogroup" aria-label="Workflow">
        {GROUPS.map((g) => {
          const active = activeGroup?.id === g.id;
          const cls = [
            "mode-picker__option",
            active && "mode-picker__option--active",
            g.disabled && "mode-picker__option--disabled",
          ].filter(Boolean).join(" ");
          return (
            <button
              key={g.id}
              type="button"
              role="radio"
              aria-checked={active}
              aria-disabled={g.disabled || undefined}
              disabled={g.disabled}
              className={cls}
              onClick={() => !active && onChange(g.defaultMode)}
            >
              <span className="mode-picker__icon">{ICONS[g.id]}</span>
              <span className="mode-picker__text">
                <span className="mode-picker__label">
                  {g.label}
                  {g.disabled && <span className="mode-picker__badge">Coming soon</span>}
                </span>
                <span className="mode-picker__hint">{g.hint}</span>
              </span>
            </button>
          );
        })}
      </div>

      {showTabs && (
        <div className="mode-tabs" role="tablist" aria-label={`${activeGroup.label} actions`}>
          {activeGroup.modes.map((m) => (
            <button
              key={m.value}
              type="button"
              role="tab"
              aria-selected={value === m.value}
              className={`mode-tabs__tab${value === m.value ? " mode-tabs__tab--active" : ""}`}
              onClick={() => onChange(m.value)}
            >
              {m.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}