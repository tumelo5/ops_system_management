import api from './axios';

// Correction Workflow — edit a Client in place (only allowed pre-link;
// backend returns 409 if this client is already linked to a batch)
export const correctClient = async (clientId, clientName, reason) => {
  const res = await api.patch(`/warehouse/clients/${clientId}/correct/`, {
    client_name: clientName,
    reason,
  });
  return res.data;
};

// Correction Workflow — edit a Model in place (same pre-link restriction)
export const correctModel = async (modelId, modelName, reason) => {
  const res = await api.patch(`/warehouse/models/${modelId}/correct/`, {
    model_name: modelName,
    reason,
  });
  return res.data;
};

// Correction Workflow — edit a Version in place (same pre-link restriction)
export const correctModelVersion = async (versionId, version, reason) => {
  const res = await api.patch(`/warehouse/versions/${versionId}/correct/`, {
    version,
    reason,
  });
  return res.data;
};

// Correction Workflow — repoint a Batch's client and/or model_version
// (the safe path once a record is already linked/scanned)
export const submitReassignmentRequest = async (batchId, { clientId, batchCode, reason }) => {
  const res = await api.post(`/warehouse/batches/${batchId}/reassign-request/`, {
    client_id: clientId,
    batch_code:batchCode,
    reason,
  });
  return res.data;
};

// Correction Workflow — look up a batch by its code, to correct it
export const getBatchByCode = async (batchCode) => {
  const res = await api.get(`/warehouse/batches/list/?batch_code=${batchCode}`);
  return res.data;
};