import api from "./axios";

// The servicing company (a single record, set once)
export const getCompany = async () =>
  (await api.get("/warehouse/company/")).data;

export const setCompany = async (clientId) =>
  (await api.post("/warehouse/company/", { client: clientId })).data;