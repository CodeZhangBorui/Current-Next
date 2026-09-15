import axios from "axios";

export const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || "/api/v1",
  withCredentials: true,
});

export async function prepareCsrf() {
  await api.get("/auth/csrf");
}

api.interceptors.request.use((config) => {
  if (typeof FormData !== "undefined" && config.data instanceof FormData) {
    // Let the browser add the multipart boundary required by Django's parser.
    config.headers.delete("Content-Type");
  }
  if (typeof document !== "undefined") {
    const token = document.cookie.split("; ").find((item) => item.startsWith("csrftoken="))?.split("=")[1];
    if (token) config.headers["X-CSRFToken"] = decodeURIComponent(token);
  }
  return config;
});
