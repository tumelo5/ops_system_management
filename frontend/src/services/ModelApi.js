import api from "./axios";

// ---------- Lookups ----------
// Distinct model names: [{ model }]
export const getExistingModels = async () =>
  (await api.get("/warehouse/models/list/")).data;

// Versions of a model, by model name: [{ id, version }]
export const getVersionsByModel = async (modelName) =>
  (await api.get("/warehouse/versions/list/", { params: { model: modelName } })).data;

// ---------- Correction ----------
// Renames a model on every one of its versions
export const correctModel = async (oldName, newName) =>
  (await api.patch("/warehouse/models/correct/", {
    model: oldName,
    new_model: newName,
  })).data;

// Edit a version in place (same pre-link restriction as clients)
export const correctModelVersion = async (versionId, version) =>
  (await api.patch(`/warehouse/versions/${versionId}/correct/`, { version })).data;