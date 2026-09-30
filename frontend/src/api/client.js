import axios from "axios";

const baseURL = import.meta.env.VITE_API_URL || "/api/v1";

export const api = axios.create({ baseURL });

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("isapms_access");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

let refreshPromise = null;

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config || {};
    const refresh = localStorage.getItem("isapms_refresh");
    if (error.response?.status === 401 && refresh && !original._retry && !original.url?.includes("/auth/login/")) {
      original._retry = true;
      refreshPromise =
        refreshPromise ||
        axios
          .post(`${baseURL}/auth/refresh/`, { refresh })
          .then((response) => {
            localStorage.setItem("isapms_access", response.data.access);
            if (response.data.refresh) localStorage.setItem("isapms_refresh", response.data.refresh);
            return response.data.access;
          })
          .finally(() => {
            refreshPromise = null;
          });
      try {
        const access = await refreshPromise;
        original.headers = original.headers || {};
        original.headers.Authorization = `Bearer ${access}`;
        return api(original);
      } catch (refreshError) {
        localStorage.removeItem("isapms_access");
        localStorage.removeItem("isapms_refresh");
        localStorage.removeItem("isapms_user");
      }
    }
    return Promise.reject(error);
  }
);

export function errorMessage(error) {
  const data = error?.response?.data;
  if (!data) return "Unable to reach the server. Check that the API is running.";
  if (data.errors && typeof data.errors === "object" && !Array.isArray(data.errors)) {
    return Object.entries(data.errors)
      .map(([field, messages]) => `${field}: ${[].concat(messages).join(" ")}`)
      .join(" ");
  }
  if (Array.isArray(data.errors)) return data.errors.map(String).join(" ");
  return data.detail || "The request could not be completed.";
}

export async function fetchAll(path, params = {}) {
  const response = await api.get(path, { params: { page_size: 100, ...params } });
  return response.data;
}
