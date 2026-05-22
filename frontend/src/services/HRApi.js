import api from './axios';

// HR Workflow  
export const HRApi = {

    registerEmployee: async (formData) => {
        const response = await api.post("/hr/employees/", {
            mode: "register_employee",
            ...formData
        });
        return response.data;
    }

};
