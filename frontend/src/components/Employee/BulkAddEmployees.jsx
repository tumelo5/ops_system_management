import { useState } from "react";
//import axios from "axios";
import { bulkCreateEmployees } from "../../services/employeeApi";

function BulkAddEmployees() {
  const [rows, setRows] = useState([
    { full_name: "", title: "", department: "", employement_status: "", email: "" }
  ]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  // Update field value in the state
  const handleChange = (index, field, value) => {
    const updated = [...rows];
    updated[index][field] = value;
    setRows(updated);
  };

  // Add a new empty row
  const addRow = () => {
    setRows([...rows, { full_name: "", title: "", department: "", employement_status: "", email: "" }]);
  };

  // Remove a row
  const removeRow = (index) => {
    setRows(rows.filter((_, i) => i !== index));
  };

  // Submit all rows to the backend
  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    if (rows.length === 0) {
      setError("At least one employee is required.");
      setLoading(false);
      return;
    }

    setLoading(true);

    try {
      // call the API function from employeeApi.js
      const response = await bulkCreateEmployees(rows);

      if (response.data.success) {
        alert(`${response.data.count} employees created successfully.`);
        // Reset form after successful submit
        setRows([{ full_name: "", title: "", department: "", employement_status: "", email: "" }]);
      } else {
        setError(response.data.message || "Bulk creation failed.");
      }
    } catch (err) {
      console.error(err);
      setError("An error occurred while submitting.");
    }

    setLoading(false);
  };

  return (
    <div>
      <h2>Bulk Add Employees</h2>

      {error && <p style={{ color: "red" }}>{error}</p>}

      <form onSubmit={handleSubmit}>
        {rows.map((row, index) => (
          <div key={index} style={{ marginBottom: "10px" }}>
            <input
              placeholder="Full Name"
              value={row.full_name}
              onChange={(e) => handleChange(index, "full_name", e.target.value)}
            />

            <input
              placeholder="Title"
              value={row.title}
              onChange={(e) => handleChange(index, "title", e.target.value)}
            />

            <input
              placeholder="Department"
              value={row.department}
              onChange={(e) => handleChange(index, "department", e.target.value)}
            />

            <input
              placeholder="Employment Status"
              value={row.employement_status}
              onChange={(e) => handleChange(index, "employement_status", e.target.value)}
            />

            <input
              placeholder="Email"
              value={row.email}
              onChange={(e) => handleChange(index, "email", e.target.value)}
            />

            {rows.length > 1 && (
              <button type="button" onClick={() => removeRow(index)}>
                Remove
              </button>
            )}
          </div>
        ))}

        <button type="button" onClick={addRow}>
          + Add Row
        </button>

        <br /><br />

        <button type="submit" disabled={loading}>
          {loading ? "Submitting..." : "Bulk Add"}
        </button>
      </form>
    </div>
  );
}

export default BulkAddEmployees;
