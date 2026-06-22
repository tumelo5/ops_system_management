import api from './axios';


// Client Workflow
export const submitClientWorkflow = async (payload) => {
  const { type, ...rest } = payload;

  const res = await api.post("/warehouse/clients/", {
    mode: type,
    ...rest
  });

  return res.data;
};


// Device Workflow
export const submitDeviceWorkflow = async (payload) => {
  const { type, ...rest } = payload;

  const res = await api.post("/warehouse/devices/", { mode: type, ...rest });

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