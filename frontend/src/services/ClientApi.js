import api from './axios';

// Client Workflow — Bulk clients (base step: create clients + models)
export const submitBulkClientsBase = async (payload) => {
  const res = await api.post("/warehouse/clients/bulk/base/", payload);
  return res.data;
};

// Client Workflow — Bulk clients (linking step: batch codes + versions)
export const submitBulkClientsLinking = async (payload) => {
  const res = await api.post("/warehouse/clients/bulk/links/", payload);
  return res.data;
};

// Client Workflow — Existing client: validate selection
export const validateExistingSelection = async (payload) => {
  const res = await api.post("/warehouse/clients/existing/validate/", payload);
  return res.data;
};

// Client Workflow — Existing client: new version
export const submitNewVersion = async (payload) => {
  const res = await api.post("/warehouse/clients/existing/new-version/", payload);
  return res.data;
};

// Client Workflow — Existing client: new model
export const submitNewModel = async (payload) => {
  const res = await api.post("/warehouse/clients/existing/new-model/", payload);
  return res.data;
};

// Device Workflow — scan a device
export const scanDevice = async (payload) => {
  const res = await api.post("/warehouse/devices/scan/", payload);
  return res.data;
};

// Device Workflow — confirm a single device
export const confirmDevice = async (payload) => {
  const res = await api.post("/warehouse/devices/confirm/", payload);
  return res.data;
};

// Device Workflow — confirm multiple devices
export const confirmBulkDevices = async (payload) => {
  const res = await api.post("/warehouse/devices/confirm-bulk/", payload);
  return res.data;
};

// Get existing clients
export const getExistingClients = async () => {
  const res = await api.get("/warehouse/clients/list/");
  return res.data;
};

// Get existing models
export const getExistingModels = async () => {
  const res = await api.get("/warehouse/models/list/");
  return res.data;
};

// Get versions by model
export const getVersionsByModel = async (modelId) => {
  const res = await api.get(`/warehouse/versions/list/?model=${modelId}`);
  return res.data;
};

// Device Workflow: assign rental devices to a client (bulk)
export const submitRentals = async (payload) => {
  const res = await api.post("/warehouse/devices/rentals/", payload);
  return res.data;
};

// Rentals: look up the active rental for a serial number
export const getActiveRental = async (serialNumber) => {
  const res = await api.get("/warehouse/devices/rentals/active/", {
    params: { serial_number: serialNumber },
  });
  return res.data;
};
 
// Rentals: end a rental
export const endRental = async (payload) => {
  const res = await api.post("/warehouse/devices/rentals/end/", payload);
  return res.data;
};

export const getCompany = async () => {
  const res = await api.get("/warehouse/company/");
  return res.data;
};
 
// Company: set it (once only)
export const setCompany = async (clientId) => {
  const res = await api.post("/warehouse/company/", { client: clientId });
  return res.data;
};


// Rentals: can this serial number be rented right now? (scan-time check)
export const checkRentable = async (serialNumber) => {
  const res = await api.get("/warehouse/devices/rentals/check/", {
    params: { serial_number: serialNumber },
  });
  return res.data;
};
 
// Rentals: end many rentals at once with one end date (all-or-nothing)
export const endRentals = async (payload) => {
  const res = await api.post("/warehouse/devices/rentals/end/bulk/", payload);
  return res.data;
};

export const getClientsAwaitingLinking = async () => {
  const res = await api.get("/warehouse/clients/awaiting-linking/"); // same instance and prefix as getExistingClients
  return res.data;
};