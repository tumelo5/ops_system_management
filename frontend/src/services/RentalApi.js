// Rental endpoints for the Warehouse module.
//
// ADAPT (2 lines): use the same axios instance ClientApi.js uses (the one that
// attaches the JWT), and set BASE to wherever the warehouse urls are mounted.
import api from "./api";

const BASE = "/warehouse/rentals";

// Scan-time check: does the SN exist, what is its id, can it be assigned?
export const checkAssignable = async (serialNumber) =>
  (await api.get(`${BASE}/check/`, { params: { serial_number: serialNumber } })).data;

// Active rental for an SN (404 = not currently on rent)
export const getActiveRental = async (serialNumber) =>
  (await api.get(`${BASE}/active/`, { params: { serial_number: serialNumber } })).data;

// items: [{ device, rental_client, expected_return_date }]
export const assignRentals = async (items) => (await api.post(`${BASE}/`, items)).data;

// { rental_id, end_date: "YYYY-MM-DD" }
export const endRental = async ({ rental_id, end_date }) =>
  (await api.post(`${BASE}/end/`, { rental_id, end_date })).data;

// Pulls the first readable message out of the shapes this API returns:
// { error }, { detail }, a list of per-item error objects, or { field: [msgs] }.
export function getErrorMessage(error, fallback) {
  const pick = (v) => {
    if (!v) return null;
    if (typeof v === "string") return v;
    if (Array.isArray(v)) {
      for (const item of v) {
        const m = pick(item);
        if (m) return m;
      }
      return null;
    }
    if (typeof v === "object") {
      if (v.error) return pick(v.error);
      for (const key of Object.keys(v)) {
        const m = pick(v[key]);
        if (m) return m;
      }
    }
    return null;
  };
  return pick(error?.response?.data) || fallback;
}