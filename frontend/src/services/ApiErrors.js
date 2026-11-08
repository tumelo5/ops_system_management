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