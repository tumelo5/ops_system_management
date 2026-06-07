import RegisterEmployeeForm from "../components/hr/RegisterEmployeeForm";
import "../styles/pages/hr-dashboard.css";

export default function HRPage() {
    return (
        <div className="hr-dashboard">
            <header className="hr-dashboard__header">
                <h1 className="hr-dashboard__title">HR Dashboard</h1>
                <p className="hr-dashboard__subtitle">Register new employees and manage access</p>
            </header>
            <RegisterEmployeeForm />
        </div>
    );
}
