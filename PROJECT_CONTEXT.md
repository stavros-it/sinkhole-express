# PROJECT_CONTEXT.md — Sinkhole Express

> Context file for AI coding agents (OpenCode / Cursor / Roo / Claude Code).
> Keep this file up to date when architecture, endpoints, or file layout change.

---

## 1. Purpose

A lightweight Windows 11 desktop utility to **view and toggle Pi-hole v6
DNS blocking ON/OFF** and display key statistics, without opening the Pi-hole
web admin. Runs as a windowless `.pyw` (no console). Two editions share the
same backend logic:

- **`sinkhole_express_ctk.pyw`** — primary edition, CustomTkinter UI (modern, dark).
- **`sinkhole_express.pyw`** — classic edition, standard Tkinter/ttk UI (fallback,
  fewer dependencies; does NOT include the stats panel or the settings window —
  it still uses the older inline-settings layout).

The CTk edition is the one under active development. Feature parity with the
Tkinter edition is not maintained; treat the Tkinter file as a minimal fallback.

---

## 2. Target environment

- **OS:** Windows 11 (primary). Code is cross-platform but paths/credential
  store assume Windows.
- **Python:** 3.12 (python.org standard installer, `pythonw.exe` for launch).
- **Pi-hole:** v6.x (REST API on `pihole-FTL`, NOT the legacy v5 `api.php`).
- **Launch:** double-click `.pyw`, or via desktop shortcut created by the
  bundled `.bat`.

---

## 3. File inventory

| File | Role |
|------|------|
| `sinkhole_express_ctk.pyw` | Main app — CustomTkinter edition (active) |
| `sinkhole_express.pyw` | Fallback app — Tkinter edition |
| `sinkhole_express.ico` | Multi-res Windows icon (256→16px) |
| `sinkhole_express_icon.png` | 512px PNG preview of the icon |
| `install_dependencies.bat` | Installs `keyring` + `customtkinter` via pip |
| `create_desktop_shortcut.bat` | Creates desktop shortcut(s) for both editions |
| `PROJECT_CONTEXT.md` | This file |

There is **no** `requirements.txt`; dependencies are installed by the `.bat`.

---

## 4. Dependencies

- `customtkinter` — UI (CTk edition only).
- `keyring` — secure password storage in Windows Credential Manager.
- Standard library: `tkinter`, `urllib.request`, `urllib.error`, `ssl`,
  `json`, `os`, `threading`.

`tkinter` ships with the standard Windows Python installer; no separate install.

---

## 5. Configuration & persistence

Two separate stores — **never** put the password in the config file.

1. **Connection settings** → JSON file
   - Path: `%APPDATA%\SinkholeExpress\config.json`
     (falls back to `~/.config/SinkholeExpress/config.json` off-Windows).
   - Keys: `host` (str), `port` (int), `https` (bool).
   - Read by `load_config()`, written by `save_config(host, port, https)`.

2. **App password** → Windows Credential Manager (via `keyring`)
   - Service name: `SinkholeExpress`, account: `app_password`.
   - `load_password()`, `save_password(pw)`, `delete_password()`.
   - CAVEAT: any process running as the same Windows user can read this back.
     Acceptable for a personal workstation; note it for shared machines.

Both editions share the same config file and credential entry, so settings
carry over between them.

---

## 6. Pi-hole v6 API usage

Base URL built as: `{http|https}://{host}:{port}/api`

Client class: `PiHoleAPI(base_url)` — session-based auth.

| Method | HTTP | Endpoint | Notes |
|--------|------|----------|-------|
| `authenticate(password)` | POST | `/auth` | Body `{"password": ...}`. Returns SID from `session.sid`; raises if `session.valid` is false. |
| `get_status()` | GET | `/dns/blocking` | Returns `"enabled"` / `"disabled"`. |
| `set_blocking(enabled, timer=None)` | POST | `/dns/blocking` | Body `{"blocking": bool, "timer": seconds|null}`. `timer` enables temporary disable (currently always None in UI). |
| `get_stats()` | GET | `/stats/summary` | Returns `queries{}`, `clients{}`, `gravity{}`. CTk edition only. |
| `update_gravity()` | POST | `/action/gravity` | Rebuilds blocklists. Returns **plain-text** progress log, NOT JSON — call with `raw=True` and a long timeout (180s). Can take 20-60s. |
| `get_version()` | GET | `/info/version` | Returns `version.{core,web,ftl}.{local,remote}.version`. Used to flag update-available. |
| `logout()` | DELETE | `/auth` | Called on window close. |

Auth header for authenticated requests: `X-FTL-SID: <sid>`.

**Stats fields consumed** (`/stats/summary`):
- `queries.total`, `queries.blocked`, `queries.percent_blocked`,
  `queries.cached`
- `clients.active`
- `gravity.domains_being_blocked`

### TLS handling
- `make_tls_context()` disables cert verification when `VERIFY_TLS = False`
  (module-level constant, default False) — required for Pi-hole's self-signed
  cert. Set True only with a valid/trusted cert.

### `_request` signature
`_request(method, path, body=None, timeout=10, raw=False)` — `raw=True` returns
the response body as a string instead of JSON-parsing it (needed for the gravity
endpoint, which streams plain text). `timeout` is per-call (gravity uses 180s).

### Error handling (in `PiHoleAPI._request`)
- `HTTPError` → surfaces Pi-hole's JSON `error.message`.
- `URLError` with `SSLError` reason → hints that HTTPS may be wrong / suggests
  unticking HTTPS.
- Other `URLError` → "cannot reach" with host/port/scheme hint.

---

## 7. Known Pi-hole port gotcha (IMPORTANT)

Pi-hole v6 default HTTPS port is **8443**, NOT 443. But installations vary.
Check real ports on the Pi with:

```
sudo pihole-FTL --config webserver.port
```

Output uses suffix flags: `o` = redirect, `s` = TLS. Example seen in this
project: `82o,443os,[::]:82o,[::]:443os` → HTTP on **82**, HTTPS on **443**.

UI behavior: toggling the HTTPS switch auto-fills the port with a sensible
default (`_on_https_toggle`): HTTPS→443, HTTP→80, but only when the field still
holds the *other* scheme's default, so manual overrides are preserved.

---

## 8. CTk edition UI structure (`App(ctk.CTk)`)

Layout, top → bottom:
1. Header label "Sinkhole Blocking".
2. **Gear button** `⚙` — `place()`d top-right (`relx=1.0, anchor="ne"`), always
   visible; opens Settings window.
3. Status label — `● ENABLED` (green) / `● DISABLED` (amber) / transient states.
4. **Toggle button** — recolors by state: red (`#d32f2f`) "■ Disable Blocking"
   when ON, green (`#2e7d32`) "▶ Enable Blocking" when OFF.
5. Refresh button (outline).
6. **Statistics panel** — 2-column grid of 6 color-coded metric cells.
7. **Bottom action row** — packed `side="bottom"` (so it can never be clipped):
   `⚙ Settings` (filled) + `Reconnect` (outline).

Window: 380×600, non-resizable. `appearance_mode="dark"`, theme `"blue"`.

### Settings window (`open_settings` → `CTkToplevel`)
Holds all editable connection values: host, port, HTTPS switch, masked password
(`show="•"`) + Show checkbox, and Save & Connect / Clear stored buttons.
- The `StringVar`/`BooleanVar`s live on the **App** instance (not the popup),
  so connect logic and launch auto-connect work whether or not the popup was
  opened.
- `_settings_win` guards against opening duplicates (re-focuses existing).
- `save_and_connect()` returns bool; popup closes only on success.
- Validation failures raise a `messagebox.showwarning` so they surface over the
  popup.

### Icon
`_set_window_icon(win)` calls `win.iconbitmap()` with `sinkhole_express.ico`
resolved relative to the script dir. `.ico` must sit next to the `.pyw`.
Toplevel re-applies icon via `after(200, ...)` due to a timing quirk.

---

## 9. Threading model

All network calls run off the UI thread via `App._run(fn, on_done)`:
- `fn` runs in a `threading.Thread(daemon=True)`.
- Result/exception marshalled back to UI thread with `self.after(0, ...)`.
- `on_done(result, err)` pattern; `_on_status` is the main callback.

`connect()` and `on_toggle()` build a `task()` closure that authenticates /
sets blocking, then fetches status AND stats. Stats fetch is wrapped in
try/except and is **non-critical** — failure keeps the toggle working and
leaves the last stats values in place.

`_on_status(result, err)` unpacks `(status, stats)` tuple. On error it shows a
messagebox and disables the toggle button.

---

## 10. Batch scripts

- **`install_dependencies.bat`** — checks Python on PATH, upgrades pip, installs
  `keyring customtkinter`. Pauses on completion/error.
- **`create_desktop_shortcut.bat`** — resolves the REAL Desktop via
  PowerShell `[Environment]::GetFolderPath('Desktop')` (handles OneDrive-
  redirected desktops, which was a real bug here: `%USERPROFILE%\Desktop` did
  not exist). Finds `pythonw.exe` via `where`. Writes a temp `.ps1` to build
  each shortcut via `WScript.Shell` (avoids caret line-continuation quoting
  bugs). Sets target=pythonw, arguments=quoted `.pyw` path, working dir, and
  the `.ico`. Creates "Sinkhole Express" (CTk) and "Sinkhole Express (Classic)".

---

## 11. Conventions & preferences

- Windowless launch: `.pyw` + `pythonw.exe`.
- Keep the two-store split (config JSON vs. credential manager) — do not write
  the password to disk in plaintext.
- Prefer standard-library HTTP (`urllib`) over adding `requests` as a dep.
- Network calls must stay off the UI thread (use `_run`).
- Colors: green `#2e7d32`/`#4caf50` = enabled/positive, red `#d32f2f`/`#e05555`
  = disabled/blocked, amber `#e0a030` = warning/disabled-status.
- Author's broader "SA tool family" convention: CustomTkinter + PyInstaller
  `.exe` packaging, `.pyw` launchers, Greek-language end-user guides for
  non-technical users (not yet produced for this app).

---

## 12. Possible next steps (not yet implemented)

- Timed auto-refresh of stats (e.g. every 10s) so the panel stays live.
- Temporary-disable dropdown (5/10/30 min) wired to `set_blocking(timer=...)`.
- Port the stats panel + settings window into the Tkinter edition for parity.
- PyInstaller build script (`--onefile --windowed --icon sinkhole_express.ico`)
  for a self-contained `.exe`.
- Greek-language HTML user guide (per author's usual pattern).
- Multi-Pi-hole support (profiles / dropdown).
