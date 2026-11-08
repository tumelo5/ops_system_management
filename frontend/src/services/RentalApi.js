import api from "./axios";

// Scan-time check on Assign Rental: can this SN be rented right now?
export const checkRentable = async (serialNumber) =>
  (await api.get("/warehouse/devices/rentals/check/", {
    params: { serial_number: serialNumber },
  })).data;

// Scan on End Rental: active rental for an SN (404 = not on rent)
export const getActiveRental = async (serialNumber) =>
  (await api.get("/warehouse/devices/rentals/active/", {
    params: { serial_number: serialNumber },
  })).data;

// Assign company-owned devices to a client (bulk)
export const submitRentals = async (payload) =>
  (await api.post("/warehouse/devices/rentals/", payload)).data;

// End one rental: { rental_id, end_date }
export const endRental = async (payload) =>
  (await api.post("/warehouse/devices/rentals/end/", payload)).data;

// End many rentals with one end date, all-or-nothing: { rental_ids, end_date }
export const endRentals = async (payload) =>
  (await api.post("/warehouse/devices/rentals/end/bulk/", payload)).data;