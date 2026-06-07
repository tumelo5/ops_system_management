import api from './axios';

// Client Workflow
// to be looked into both client and bulk flow since they seem to be doing the same thing, 
// maybe we can merge them into one function and just pass the type as an argument 
export const submitClientWorkflow = async (payload) => {
  const { type, ...rest } = payload;

  const res = await api.post("/warehouse/api/handle/", {
    mode: type,
    ...rest
  });

  return res.data;
};


// Bulk Workflow, to be looked into both client and bulk flow since they seem to be doing the same thing, 
// maybe we can merge them into one function and just pass the type as an argument 
export const submitBulkWorkflow = async (payload) => {
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


// Scan Device
export const submitScanWorkflow = async (payload) =>{
  const {type, ...rest} = payload;
  const res = await api.post("/warehouse/devices/", {mode: type, ...rest});
  return res.data

};

// Get existing clients,
// for adding devices to exsiting clients
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