// services/authApi.js
import api from '../api/axios';

export const AuthApi = {
    login: async (username, password) => {
        const response = await api.post("/auth/login/", { username, password });
        const { access, refresh, department, full_name } = response.data;

        localStorage.setItem("access", access);
        localStorage.setItem("refresh", refresh);
        localStorage.setItem("department", department);
        localStorage.setItem("full_name", full_name);

        return response.data;
    },

    logout: async () => {
        const refresh = localStorage.getItem("refresh");
        await api.post("/auth/logout/", { refresh });

        localStorage.removeItem("access");
        localStorage.removeItem("refresh");
        localStorage.removeItem("department");
        localStorage.removeItem("full_name");
    },

    me: async () => {
        const response = await api.get("/auth/me/");
        return response.data;
    },

    isAuthenticated: () => !!localStorage.getItem("access"),

    getDepartment: () => localStorage.getItem("department"),

    getFullName: () => localStorage.getItem("full_name"),
};