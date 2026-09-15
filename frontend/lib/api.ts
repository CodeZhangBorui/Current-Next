import axios from "axios";

export const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || "/api/v1",
  withCredentials: true,
  headers: { "Content-Type": "application/json" },
});

export async function prepareCsrf() {
  await api.get("/auth/csrf");
}

api.interceptors.request.use((config) => {
  if (typeof document !== "undefined") {
    const token = document.cookie.split("; ").find((item) => item.startsWith("csrftoken="))?.split("=")[1];
    if (token) config.headers["X-CSRFToken"] = decodeURIComponent(token);
  }
  return config;
});
