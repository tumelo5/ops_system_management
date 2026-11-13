import { useState } from "react";
import { scanDevice } from "../../../services/DeviceApi";
import Notification, { useNotification } from "./Notifications";

// Props:
//   unlocked - scanning is only allowed once a batch exists for the flow
//   embedded - removes the standalone card wrapper when used inside another card
export default function ScanCard({ unlocked, embedded = false }) {
  const [serialNumber, setSerialNumber] = useState("");
  const [note, notify, clearNote] = useNotification();

  const handleSerialKeyDown = async (e) => {
    if (e.key !== "Enter") return;

    e.preventDefault();

    const serial = serialNumber.trim();
    if (!serial) return;

    // Clear immediately so the next scan can start while this one is in flight
    setSerialNumber("");
    clearNote();

    try {
      const response = await scanDevice({ serial_number: serial });
      notify("success", `${response.serial_number || serial}: success`);
    } catch (error) {
      notify(
        "error",
        `${serial}: ${error.response?.data?.error || "Failed to scan device."}`
      );
      console.error("Scan failed:", error.response?.data);
    }
  };

  const content = (
    <>
      <h2 className={embedded ? "bulk-workflow__card-subtitle" : "bulk-workflow__card-title"}>
        Scan Device
      </h2>

      <div className="bulk-workflow__field bulk-workflow__scan-input">
        <label className="bulk-workflow__field-label" htmlFor="scan-device-serial">
          Serial Number
        </label>
        <input
          id="scan-device-serial"
          placeholder="Enter serial number — press Enter to scan"
          value={serialNumber}
          onChange={(e) => setSerialNumber(e.target.value)}
          onKeyDown={handleSerialKeyDown}
          disabled={!unlocked}
          autoFocus
        />
      </div>

      {!unlocked && (
        <p className="bulk-workflow__scan-hint">
          Confirm a client and batch before scanning devices.
        </p>
      )}

      <Notification state={note} />
    </>
  );

  return (
    <section
      className={`bulk-workflow__scan${embedded ? " bulk-workflow__scan--embedded" : ""}`}
    >
      {embedded ? (
        content
      ) : (
        <div className="bulk-workflow__card">{content}</div>
      )}
    </section>
  );
}