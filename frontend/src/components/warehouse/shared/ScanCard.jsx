import { useState, useEffect } from "react";
import { scanDevice, confirmBulkDevices } from "../../../services/ClientApi";
import Notification, { useNotification } from "./Notifications";

// Props:
//   unlocked      - scanning is only allowed once a batch exists for the flow
//   onSaved       - called after Save All succeeds (the panel decides what to reset)
//   onDirtyChange - called with true/false when there are unsaved scanned devices
export default function ScanCard({ unlocked, onSaved, onDirtyChange }) {
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
    if (scannedDevices.some((d) => d.serial_number === serial)) {
      notify("error", `${serial} already scanned.`);
      return;
    }
    clearNote();
    try {
      const response = await scanDevice({ serial_number: serial });
      setScannedDevices((prev) => [...prev, response.device]);
      setSerialNumber("");
    } catch (error) {
      notify("error", error.response?.data?.error || "Failed to scan device.");
      console.error("Scan failed:", error.response?.data);
    }
  };

  const handleRemove = (serial_number) => {
    setScannedDevices((prev) => prev.filter((d) => d.serial_number !== serial_number));
  };

  const handleSaveAll = async () => {
    if (scannedDevices.length === 0) return;
    clearNote();
    try {
      const response = await confirmBulkDevices({
        serial_numbers: scannedDevices.map((d) => d.serial_number),
      });
      setScannedDevices([]);
      setSerialNumber("");
      notify("success", response.message || "All devices saved and activated.");
      onSaved?.();
    } catch (error) {
      notify("error", error.response?.data?.error || "Failed to save devices.");
      console.error("Save all failed:", error);
    }
  };

  return (
    <section className="bulk-workflow__scan">
      <div className="bulk-workflow__card">
        <h2 className="bulk-workflow__card-title">Scan Device</h2>

        <div className="bulk-workflow__field bulk-workflow__scan-input">
          <input
            placeholder="Serial number — press Enter to add"
            value={serialNumber}
            onChange={(e) => setSerialNumber(e.target.value)}
            onKeyDown={handleSerialKeyDown}
            disabled={!unlocked}
          />
        </div>

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
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {scannedDevices.map((device) => (
                  <tr key={device.serial_number}>
                    <td>{device.serial_number}</td>
                    <td>{device.client_name}</td>
                    <td>{device.batch_code}</td>
                    <td>{device.model_name}</td>
                    <td>{device.version_name}</td>
                    <td>{device.status}</td>
                    <td>
                      <button
                        type="button"
                        className="bulk-workflow__btn-remove"
                        onClick={() => handleRemove(device.serial_number)}
                        title="Remove"
                      >
                        🗑
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>

            <div style={{ display: "flex", justifyContent: "flex-end", marginTop: "0.5rem" }}>
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
      </div>
    </section>
  );
}