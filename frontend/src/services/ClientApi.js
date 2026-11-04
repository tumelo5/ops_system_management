import api from './axios';

// Client Workflow — Bulk clients (base step: create clients only)
// payload: { clients: [{ client_name }] }
export const submitBulkClientsBase = async (payload) => {
  const res = await api.post("/warehouse/clients/bulk/base/", payload);
  return res.data;
};

// Client Workflow — Bulk clients (linking step: batch code + model + version per client)
// payload: { links: [{ client, model, version, batch_code }] }
export const submitBulkClientsLinking = async (payload) => {
  const res = await api.post("/warehouse/clients/bulk/links/", payload);
  return res.data;
};

// Client Workflow — Existing client: validate selection
// payload: { client, version }   (version = id of the model/version row)
// response: { batch_exists, batch_code, message? }
export const validateExistingSelection = async (payload) => {
  const res = await api.post("/warehouse/clients/existing/validate/", payload);
  return res.data;
};

// Client Workflow — Existing client: link a new batch code to a model and version.
// The model/version row is reused if it exists and created if it does not.
// payload: { client, model, version, batch_code }
export const submitExistingClientBatch = async (payload) => {
  const res = await api.post("/warehouse/clients/existing/batch/", payload);
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

// Get existing models: distinct model names, e.g. [{ model }]
export const getExistingModels = async () => {
  const res = await api.get("/warehouse/models/list/");
  return res.data;
};

// Get the versions of a model, by model name: [{ id, version }]
export const getVersionsByModel = async (modelName) => {
  const res = await api.get("/warehouse/versions/list/", {
    params: { model: modelName },
  });
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

// Correct a model: renames it on every one of its versions
export const correctModel = async (oldName, newName, reason) => {
  const res = await api.patch("/warehouse/models/correct/", {
    model: oldName,
    new_model: newName,
    reason,
  });
  return res.data;
};