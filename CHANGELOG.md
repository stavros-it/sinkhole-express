# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Planned
- Timed auto-refresh of stats (e.g. every 10 s) so the panel stays live.
- Temporary-disable dropdown (5 / 10 / 30 min) wired to `set_blocking(timer=…)`.
- PyInstaller build script for a self-contained `.exe`.
- Greek-language HTML user guide.
- Multi-Pi-hole support (profiles / dropdown).

## [1.0.0] - 2026-08-17

### Added
- Initial public release of **Sinkhole Express**.
- **Sinkhole Express** (`sinkhole_express.pyw`) — CustomTkinter UI:
  - One-click toggle of Pi-hole v6 DNS blocking ON/OFF.
  - Live status indicator (green `● ENABLED` / amber `● DISABLED`) with color-coded
    toggle button (red "Disable" when ON, green "Enable" when OFF).
  - Statistics panel (today's totals): total queries, blocked, % blocked,
    domains on list, active clients, cached — each in a color-coded cell.
  - Pi-hole version panel showing CORE / WEB / FTL versions, with an
    "update available" hint when local differs from remote.
  - **Update Gravity** button — triggers `pihole -g` via the REST API
    (streams plain-text progress, ~20–60 s).
  - Settings window: host, port, HTTPS switch, masked app password with
    show/hide toggle, Save & Connect / Clear stored buttons.
  - Auto-connect on launch when credentials are already stored.
  - Transparent re-auth on session expiry (HTTP 401) during refresh.
- Windowless launch via `.pyw` + `pythonw.exe` (no console window).
- Bundled multi-resolution Windows icon (`sinkhole_express.ico`, 256→16 px)
  and 512 px PNG preview (`sinkhole_express_icon.png`).
- `install_dependencies.bat` — installs `keyring` + `customtkinter` via pip.
- `create_desktop_shortcut.bat` — creates the "Sinkhole Express" desktop
  shortcut via `pythonw.exe`, with OneDrive-redirected desktop resolution.
- `PROJECT_CONTEXT.md` — architecture / endpoints reference for AI coding agents.
- Configuration persisted to `%APPDATA%\SinkholeExpress\config.json`
  (host, port, https) — never writes the password to disk.
- App password stored in Windows Credential Manager via `keyring`
  (service `SinkholeExpress`, account `app_password`).
- `README.md` with app icon, feature overview, install/usage docs, API
  endpoint table, port gotcha, security notes, and roadmap.
- Screenshots of both blocking-enabled and blocking-disabled states.
- MIT License.

### Security
- The Pi-hole app password is stored only in the Windows Credential Manager
  (via `keyring`), never written to the config file in plaintext. Note that
  any process running as the same Windows user can read it back — acceptable
  for a personal workstation; documented for shared machines.

### Known limitations
- No timed auto-refresh of stats yet (manual Refresh only).
- No timed disable (the API's `timer` parameter is wired in the client but
  not exposed in the UI).
- The Pi-hole v6 REST API exposes no endpoint for `pihole -up` (component
  update) — only `gravity`, `restartdns`, and `flush/*` actions. The app
  shows the standard "run `pihole -up` on the Pi" hint and cannot trigger
  the update remotely.

[Unreleased]: https://github.com/stavros-it/sinkhole-express/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/stavros-it/sinkhole-express/releases/tag/v1.0.0
