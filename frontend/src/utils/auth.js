const VALID_DEPARTMENTS = ["warehouse", "repairs", "stores", "finance"];

export const DEPARTMENT_ROUTES = {
  warehouse: "/warehouse",
  repairs: "/repairs",
  stores: "/stores",
  finance: "/finance",
};

function decodeJwtPayload(token) {
  try {
    const base64 = token.split(".")[1];
    return JSON.parse(atob(base64.replace(/-/g, "+").replace(/_/g, "/")));
  } catch {
    return null;
  }
}

export function isAccessTokenValid(token) {
  if (!token) return false;
  const payload = decodeJwtPayload(token);
  if (!payload) return false;
  if (payload.exp && Date.now() >= payload.exp * 1000) return false;
  return true;
}

export function isValidDepartment(department) {
  return VALID_DEPARTMENTS.includes(department);
}

export function getDashboardPath(department) {
  return DEPARTMENT_ROUTES[department] ?? null;
}

export function setSession({ access, refresh, department, full_name }) {
  localStorage.setItem("access", access);
  localStorage.setItem("refresh", refresh);
  localStorage.setItem("department", department);
  localStorage.setItem("full_name", full_name);
}

export function clearSession() {
  localStorage.removeItem("access");
  localStorage.removeItem("refresh");
  localStorage.removeItem("department");
  localStorage.removeItem("full_name");
}

/** Returns a valid session or clears stale/invalid auth data. */
export function getSession() {
  const access = localStorage.getItem("access");
  const department = localStorage.getItem("department");

  if (!access || !isAccessTokenValid(access)) {
    clearSession();
    return { isAuthenticated: false, department: null, dashboardPath: null };
  }

  if (!isValidDepartment(department)) {
    clearSession();
    return { isAuthenticated: false, department: null, dashboardPath: null };
  }

  return {
    isAuthenticated: true,
    department,
    dashboardPath: getDashboardPath(department),
  };
}

export function isAuthenticated() {
  return getSession().isAuthenticated;
}