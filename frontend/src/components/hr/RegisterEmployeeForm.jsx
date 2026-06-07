import { useState } from "react";
import { HRApi } from "../../services/HRApi";
import "../../styles/components/register-employee-form.css";

export default function RegisterEmployeeForm() {
    const [formData, setFormData] = useState({
        username: "",
        password: "",
        first_name: "",
        last_name: "",
        email: "",
        department: "",
        title: "",
        employee_id: "",
    });

    const [message, setMessage] = useState(null);
    const [error, setError] = useState(null);
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
                username: "",
                password: "",
                first_name: "",
                last_name: "",
                email: "",
                department: "",
                title: "",
                employee_id: "",
            });
        } catch (err) {
            setError(err.response?.data?.error || "Something went wrong.");
        } finally {
            setLoading(false);
        }
    };

    return (
        <section className="register-employee">
            <h2 className="register-employee__title">Register Employee</h2>

            {message && (
                <p className="register-employee__message register-employee__message--success">{message}</p>
            )}
            {error && (
                <p className="register-employee__message register-employee__message--error">
                    {typeof error === "object" ? JSON.stringify(error) : error}
                </p>
            )}

            <form className="register-employee__form" onSubmit={handleSubmit}>
                <div className="register-employee__field">
                    <input name="first_name" placeholder="First Name" value={formData.first_name} onChange={handleChange} required />
                </div>
                <div className="register-employee__field">
                    <input name="last_name" placeholder="Last Name" value={formData.last_name} onChange={handleChange} required />
                </div>
                <div className="register-employee__field">
                    <input name="username" placeholder="Username" value={formData.username} onChange={handleChange} required />
                </div>
                <div className="register-employee__field">
                    <input name="password" placeholder="Password" value={formData.password} onChange={handleChange} required type="password" />
                </div>
                <div className="register-employee__field">
                    <input name="email" placeholder="Email" value={formData.email} onChange={handleChange} />
                </div>
                <div className="register-employee__field">
                    <input name="employee_id" placeholder="Employee ID" value={formData.employee_id} onChange={handleChange} />
                </div>
                <div className="register-employee__field">
                    <input name="title" placeholder="Job Title" value={formData.title} onChange={handleChange} />
                </div>
                <div className="register-employee__field register-employee__field--full">
                    <select name="department" value={formData.department} onChange={handleChange} required>
                        <option value="">Select Department</option>
                        <option value="warehouse">Warehouse</option>
                        <option value="hr">Human Resources</option>
                    </select>
                </div>

                <div className="register-employee__actions">
                    <button className="register-employee__btn" type="submit" disabled={loading}>
                        {loading ? "Registering..." : "Register Employee"}
                    </button>
                </div>
            </form>
        </section>
    );
}
