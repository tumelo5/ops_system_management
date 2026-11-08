import api from "./axios";

// ---------- Correction ----------
// Look a batch up by its code
export const findBatchForCorrection = async (batchCode) =>
  (await api.get("/warehouse/batch-codes/lookup/", {
    params: { batch_code: batchCode },
  })).data;

// Correct a mistyped batch code
export const correctBatchCode = async (batchId, newCode) =>
  (await api.patch(`/warehouse/batch-codes/${batchId}/correct/`, {
    batch_code: newCode,
  })).data;