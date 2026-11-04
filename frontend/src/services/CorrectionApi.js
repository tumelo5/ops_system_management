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

// Correct a model: renames it on every one of its versions
export const correctModel = async (oldName, newName, reason) => {
  const res = await api.patch("/warehouse/models/correct/", {
    model: oldName,
    new_model: newName,
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

// Batch code correction: look a batch up by its code
export const findBatchForCorrection = async (batchCode) => {
  const res = await api.get("/warehouse/batch-codes/lookup/", { params: { batch_code: batchCode } });
  return res.data;
};

// Correct a mistyped batch code (only while nothing has been scanned or registered under it)
export const correctBatchCode = async (batchId, newCode, reason) => {
  const res = await api.patch(`/warehouse/batch-codes/${batchId}/correct/`, {
    batch_code: newCode,
    reason,
  });
  return res.data;
};