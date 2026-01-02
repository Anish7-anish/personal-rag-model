import axios from "axios";

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api",
});

export const uploadDocument = async (file) => {
  const formData = new FormData();
  formData.append("file", file);

  const { data } = await api.post("/upload", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
};

export const queryDocuments = async (payload) => {
  const { data } = await api.post("/query", payload);
  return data;
};

export default api;
