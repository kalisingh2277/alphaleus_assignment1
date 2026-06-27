# Argus Chrome Extension

One-click "monitor this page" + a toolbar badge of unread intelligence cards.

## Load (no build step)

1. Open `chrome://extensions` and enable **Developer mode** (top right).
2. Click **Load unpacked** and select this `extension/` folder.
   (Or zip the folder and drag the zip onto the page.)
3. Open **Settings** (right-click the icon → Options, or the link in the popup):
   - **Backend URL** — your Argus URL, e.g. `http://localhost:8000` or your deployed URL.
   - **API key** — must match the backend's `API_KEY` (leave blank if the backend has none).

## Use

- Click the Argus icon on any page → tweak the name / monitored section → **Add competitor**.
- The toolbar **badge** shows how many unread intelligence cards exist, polled every minute.

## How it talks to the backend

- Add: `POST /api/v1/competitors` with an `X-API-Key` header.
- Badge: `GET /api/v1/changes/unread-count` with the same header.
