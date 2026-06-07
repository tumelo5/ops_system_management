import api from "./axios";
import {
  clearSession,
  getDashboardPath,
  getSession,
  isValidDepartment,
  setSession,
} from "../utils/auth";

export const AuthApi = {
  login: async (username, password) => {
    const response = await api.post("/auth/login/", { username, password });
    const { access, refresh, department, full_name } = response.data;

    if (!isValidDepartment(department)) {
      throw new Error("Invalid department on account.");
    }

    setSession({ access, refresh, department, full_name });
    return response.data;
  },

  logout: async () => {
    const refresh = localStorage.getItem("refresh");
    try {
      if (refresh) {
        await api.post("/auth/logout/", { refresh });
      }
    } finally {
      clearSession();
    }
  },

  me: async () => {
    const response = await api.get("/auth/me/");
    return response.data;
  },

  getSession,
  getDashboardPath,
  clearSession,
};
