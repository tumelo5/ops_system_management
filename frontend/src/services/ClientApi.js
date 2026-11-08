import api from "./axios";

// ---------- Add Clients (base step: create clients only) ----------
// payload: { clients: [{ client_name, model? }] }
export const submitBulkClientsBase = async (payload) =>
  (await api.post("/warehouse/clients/bulk/base/", payload)).data;

// ---------- Linking (a client's first batch) ----------
// payload: { links: [{ client, model, version, batch_code }] }
export const submitBulkClientsLinking = async (payload) =>
  (await api.post("/warehouse/clients/bulk/links/", payload)).data;

// Clients that have no batch code yet: the Linking dropdown
export const getClientsAwaitingLinking = async () =>
  (await api.get("/warehouse/clients/awaiting-linking/")).data;

// ---------- Existing Client (every batch after the first) ----------
// payload: { client, version }  (version = id of the model/version row)
// response: { batch_exists, batch_code, message? }
export const validateExistingSelection = async (payload) =>
  (await api.post("/warehouse/clients/existing/validate/", payload)).data;

// payload: { client, model, version, batch_code }
export const submitExistingClientBatch = async (payload) =>
  (await api.post("/warehouse/clients/existing/batch/", payload)).data;

// ---------- Lookups ----------
export const getExistingClients = async () =>
  (await api.get("/warehouse/clients/list/")).data;

// ---------- Correction ----------
// Edit a client in place (backend returns 409 once it is linked to a batch)
export const correctClient = async (clientId, clientName) =>
  (await api.patch(`/warehouse/clients/${clientId}/correct/`, {
    client_name: clientName,
  })).data;