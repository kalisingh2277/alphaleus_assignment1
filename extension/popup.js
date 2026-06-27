// Popup: pre-fill the current tab, then POST it to the Argus backend.

const DEFAULT_BACKEND = "http://localhost:8000";

async function getConfig() {
  const { backendUrl, apiKey } = await chrome.storage.local.get(["backendUrl", "apiKey"]);
  return { backendUrl: backendUrl || DEFAULT_BACKEND, apiKey: apiKey || "" };
}

function setStatus(message, kind) {
  const el = document.getElementById("status");
  el.textContent = message;
  el.className = kind || "";
}

document.addEventListener("DOMContentLoaded", async () => {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (tab && tab.url) {
    document.getElementById("url").value = tab.url;
    let name = tab.title ? tab.title.slice(0, 60) : "";
    if (!name) {
      try { name = new URL(tab.url).hostname; } catch (e) { /* leave blank */ }
    }
    document.getElementById("label").value = name;
  }

  document.getElementById("add").addEventListener("click", onAdd);
  document.getElementById("openOptions").addEventListener("click", (e) => {
    e.preventDefault();
    chrome.runtime.openOptionsPage();
  });
});

async function onAdd() {
  const { backendUrl, apiKey } = await getConfig();
  const url = document.getElementById("url").value.trim();
  const name = document.getElementById("label").value.trim() || url;
  const scope = document.getElementById("scope").value;

  if (!url) { setStatus("Enter a URL first.", "err"); return; }
  setStatus("Adding…");

  try {
    const res = await fetch(`${backendUrl}/api/v1/competitors`, {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-API-Key": apiKey },
      body: JSON.stringify({ name, url, monitor_scope: scope }),
    });
    if (res.status === 201) {
      setStatus("✓ Added to Argus.", "ok");
    } else if (res.status === 401) {
      setStatus("✗ Invalid API key — check Settings.", "err");
    } else {
      setStatus(`✗ Failed (HTTP ${res.status}).`, "err");
    }
  } catch (e) {
    setStatus("✗ Cannot reach the backend — check Settings.", "err");
  }
}
