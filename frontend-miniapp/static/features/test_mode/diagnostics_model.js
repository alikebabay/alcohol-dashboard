import { api } from "../../admin_backend.js";

export async function graphTest(text) {
  const res = await api("/test/graph", "POST", { text }, false);
  if (!res.ok) throw new Error(res.error || "Test failed");
  return res.data; // array of {raw, norm, changed, ...}
}