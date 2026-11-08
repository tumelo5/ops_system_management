import { useState, useEffect } from "react";
import { scanDevice, confirmBulkDevices } from "../../../services/DeviceApi";
import Notification, { useNotification } from "./Notifications";

// Props:
//   unlocked      - scanning is only allowed once a batch exists for the flow
//   onSaved       - called after Save All succeeds (the panel decides what to reset)
//   onDirtyChange - called with true/false when there are unsaved scanned devices
//   embedded      - removes the standalone card wrapper when used inside another card
export default function ScanCard({
  unlocked,
  onSaved,
  onDirtyChange,
  embedded = false,
}) {
  const [serialNumber, setSerialNumber] = useState("");
  const [scannedDevices, setScannedDevices] = useState([]);
  const [note, notify, clearNote] = useNotification();

  useEffect(() => {
    onDirtyChange?.(scannedDevices.length > 0);
  }, [scannedDevices.length, onDirtyChange]);

  const handleSerialKeyDown = async (e) => {
    if (e.key !== "Enter") return;

    e.preventDefault();

    const serial = serialNumber.trim();
    if (!serial) return;

    if (scannedDevices.some((device) => device.serial_number === serial)) {
      notify("error", `${serial} already scanned.`);
      return;
    }

    clearNote();

    try {
      const response = await scanDevice({ serial_number: serial });
      setScannedDevices((prev) => [...prev, response.device]);
      setSerialNumber("");
    } catch (error) {
      notify(
        "error",
        error.response?.data?.error || "Failed to scan device."
      );
      console.error("Scan failed:", error.response?.data);
    }
  };

  const handleRemove = (serialNumberToRemove) => {
    setScannedDevices((prev) =>
      prev.filter((device) => device.serial_number !== serialNumberToRemove)
    );
  };

  const handleSaveAll = async () => {
    if (scannedDevices.length === 0) return;

    clearNote();

    try {
      const response = await confirmBulkDevices({
        serial_numbers: scannedDevices.map((device) => device.serial_number),
      });

      setScannedDevices([]);
      setSerialNumber("");
      notify("success", response.message || "All devices saved and activated.");
      onSaved?.();
    } catch (error) {
      notify(
        "error",
        error.response?.data?.error || "Failed to save devices."
      );
      console.error("Save all failed:", error);
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
          placeholder="Enter serial number — press Enter to add"
          value={serialNumber}
          onChange={(e) => setSerialNumber(e.target.value)}
          onKeyDown={handleSerialKeyDown}
          disabled={!unlocked}
        />
      </div>

      {!unlocked && (
        <p className="bulk-workflow__scan-hint">
          Confirm a client and batch before scanning devices.
        </p>
      )}

      <Notification state={note} />

      {scannedDevices.length > 0 && (
        <div className="bulk-workflow__device-details">
          <table className="bulk-workflow__device-table">
            <thead>
              <tr>
                <th>Serial No.</th>
                <th>Client</th>
                <th>Batch</th>
                <th>Model</th>
                <th>Version</th>
                <th>Status</th>
                <th aria-label="Actions"></th>
              </tr>
            </thead>

            <tbody>
              {scannedDevices.map((device) => (
                <tr key={device.serial_number}>
                  <td>{device.serial_number}</td>
                  <td>{device.client_name}</td>
                  <td>{device.batch_code}</td>
                  <td>{device.model}</td>
                  <td>{device.version}</td>
                  <td>{device.status}</td>
                  <td>
                    <button
                      type="button"
                      className="bulk-workflow__btn-remove"
                      onClick={() => handleRemove(device.serial_number)}
                      title="Remove"
                      aria-label={`Remove ${device.serial_number}`}
                    >
                      🗑
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          <div className="bulk-workflow__device-actions">
            <button
              type="button"
              className="bulk-workflow__btn bulk-workflow__btn--primary"
              onClick={handleSaveAll}
            >
              Save All ({scannedDevices.length})
            </button>
          </div>
        </div>
      )}
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
