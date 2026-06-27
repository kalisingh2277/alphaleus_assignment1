// Service worker: poll the backend for the unread count and show it as a badge.

const DEFAULT_BACKEND = "http://localhost:8000";
const POLL_ALARM = "argus-poll";

async function getConfig() {
  const { backendUrl, apiKey } = await chrome.storage.local.get(["backendUrl", "apiKey"]);
  return { backendUrl: backendUrl || DEFAULT_BACKEND, apiKey: apiKey || "" };
}

async function updateBadge() {
  try {
    const { backendUrl, apiKey } = await getConfig();
    const res = await fetch(`${backendUrl}/api/v1/changes/unread-count`, {
      headers: { "X-API-Key": apiKey },
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const { unread } = await res.json();
    await chrome.action.setBadgeBackgroundColor({ color: "#c0392b" });
    await chrome.action.setBadgeText({ text: unread > 0 ? String(unread) : "" });
  } catch (e) {
    await chrome.action.setBadgeText({ text: "" }); // backend unreachable → clear badge
  }
}

chrome.runtime.onInstalled.addListener(() => {
  chrome.alarms.create(POLL_ALARM, { periodInMinutes: 1 });
  updateBadge();
});

chrome.runtime.onStartup.addListener(updateBadge);

chrome.alarms.onAlarm.addListener((alarm) => {
  if (alarm.name === POLL_ALARM) updateBadge();
});
