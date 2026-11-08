import api from "./axios";

// Scan a device
export const scanDevice = async (payload) =>
  (await api.post("/warehouse/devices/scan/", payload)).data;

// Confirm a single device
export const confirmDevice = async (payload) =>
  (await api.post("/warehouse/devices/confirm/", payload)).data;

// Confirm many devices
export const confirmBulkDevices = async (payload) =>
  (await api.post("/warehouse/devices/confirm-bulk/", payload)).data;