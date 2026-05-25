import { useState } from "react";
import {HRApi} from "../../services/HRApi";

export default function RegisterEmployeeForm() {

    const [formData, setFormData] = useState({
        username:    "",
        password:    "",
        first_name:  "",
        last_name:   "",
        email:       "",
        department:  "",
        title:       "",
        employee_id: ""
    });

    const [message, setMessage] = useState(null);
    const [error,   setError]   = useState(null);
    const [loading, setLoading] = useState(false);

    const handleChange = (e) => {
        setFormData({ ...formData, [e.target.name]: e.target.value });
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        setLoading(true);
        setMessage(null);
        setError(null);

        try {
            const response = await HRApi.registerEmployee(formData);
            setMessage(response.message);
            setFormData({
                username:    "",
                password:    "",
                first_name:  "",
                last_name:   "",
                email:       "",
                department:  "",
                title:       "",
                employee_id: ""
            });
        } catch (err) {
            setError(err.response?.data?.error || "Something went wrong.");
        } finally {
            setLoading(false);
        }
    };

    return (
        <div>
            <h2>Register Employee</h2>

            {message && <p style={{ color: "green" }}>{message}</p>}
            {error && <p style={{ color: "red" }}>{typeof error === "object" ? JSON.stringify(error) : error}</p>}


            <form onSubmit={handleSubmit}>
                <input name="first_name"  placeholder="First Name"   value={formData.first_name}  onChange={handleChange} required />
                <input name="last_name"   placeholder="Last Name"    value={formData.last_name}   onChange={handleChange} required />
                <input name="username"    placeholder="Username"     value={formData.username}    onChange={handleChange} required />
                <input name="password"    placeholder="Password"     value={formData.password}    onChange={handleChange} required type="password" />
                <input name="email"       placeholder="Email"        value={formData.email}       onChange={handleChange} />
                <input name="employee_id" placeholder="Employee ID"  value={formData.employee_id} onChange={handleChange} />
                <input name="title"       placeholder="Job Title"    value={formData.title}       onChange={handleChange} />

                <select name="department" value={formData.department} onChange={handleChange} required>
                    <option value="">Select Department</option>
                    <option value="warehouse">Warehouse</option>
                    <option value="hr">Human Resources</option>
                </select>

                <button type="submit" disabled={loading}>
                    {loading ? "Registering..." : "Register Employee"}
                </button>
            </form>
        </div>
    );
};
