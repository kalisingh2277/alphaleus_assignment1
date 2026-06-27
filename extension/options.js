// Options: persist the backend URL + API key to chrome.storage.local.

const DEFAULT_BACKEND = "http://localhost:8000";

async function load() {
  const { backendUrl, apiKey } = await chrome.storage.local.get(["backendUrl", "apiKey"]);
  document.getElementById("backendUrl").value = backendUrl || DEFAULT_BACKEND;
  document.getElementById("apiKey").value = apiKey || "";
}

async function save() {
  const backendUrl = document.getElementById("backendUrl").value.trim().replace(/\/+$/, "");
  const apiKey = document.getElementById("apiKey").value.trim();
  await chrome.storage.local.set({ backendUrl: backendUrl || DEFAULT_BACKEND, apiKey });
  const status = document.getElementById("status");
  status.textContent = "Saved.";
  setTimeout(() => { status.textContent = ""; }, 1500);
}

document.addEventListener("DOMContentLoaded", () => {
  load();
  document.getElementById("save").addEventListener("click", save);
});
