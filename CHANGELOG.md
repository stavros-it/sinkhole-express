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

## [1.1.1] - 2026-08-17

### Fixed
- **Crash on non-ASCII Pi-hole responses.** `_request()` decoded the response
  body with the locale default codec; any non-ASCII byte (e.g. accented
  characters in error messages) raised `UnicodeDecodeError`. Now decodes as
  UTF-8 with `errors="replace"` in both the success and `HTTPError` paths.
- **UI freeze on window close / "Clear stored".** `App.destroy()` and
  `clear_stored()` called `api.logout()` synchronously on the UI thread with
  a 10 s network timeout — closing the window could hang for up to 10 s on a
  slow or unreachable Pi-hole. Logout now runs on a daemon thread; the
  window closes instantly. If the `DELETE /auth` doesn't land, the Pi-hole
  session expires on its own TTL.
- **Race conditions during async operations.** `connect()`, `on_toggle()`,
  `refresh()` and `on_update_gravity()` only disabled the toggle button,
  leaving Refresh / Update Gravity clickable. A second click while a request
  was in flight reused the same `PiHoleAPI` instance, causing double-auth and
  toggle-during-refresh races. All three action buttons are now disabled at
  the start of every async op and re-enabled (with correct state-aware
  gating) in the completion callback via new `_disable_actions()` /
  `_restore_actions()` helpers.
- **Stale UI after "Clear stored".** After clearing the stored password, the
  statistics panel, version label, update-available hint, toggle-button text
  and gravity button all kept their old values. They are now reset to
  defaults and the gravity button is disabled (no session).
- **`_on_status` error path didn't clear `self.current`.** A failed toggle
  left `self.current` pointing at the pre-toggle state, so a later click
  could act on a stale assumption. `self.current` is now set to `None` and
  the toggle text is reset to "Toggle" on any error.
- **`load_config()` mis-parsed hand-edited configs.** `bool("false")` is
  `True` in Python, so a config file edited by hand with `"https": "false"`
  silently enabled HTTPS. `port` and `https` are now type-coerced (port → int
  with fallback to default; https → bool via truthy-string check).
- **`sinkhole-express.desktop` icon and Exec path broken.** `Icon=sinkhole-express`
  referenced a non-existent icon name (the bundled PNG is
  `sinkhole_express_icon.png`), and `Exec=python3 sinkhole_express.pyw` used a
  relative path that only worked when launched from the source directory.
  The icon name is now `sinkhole_express_icon`, and `Exec` resolves the
  script directory via the `%k` field code with a `$PWD` fallback.
- **`install_dependencies.sh` failed on PEP 668 distros.** Modern distros
  (Ubuntu 23.04+, Fedora 38+) block `pip install --user` with
  `externally-managed-environment`. With `set -e` the script aborted there.
  It now tries `--user` first, falls back to `--break-system-packages`, and
  prints a venv-based escape hatch if both fail.
- **CI lint was a no-op for the app code.** `ruff check .` and
  `ruff format --check .` use ruff's default include (`*.py` / `*.pyi` /
  `*.ipynb`), which skips `.pyw` files — so the lint job was passing without
  ever checking `sinkhole_express.pyw`. The lint step now names the file
  explicitly: `ruff check ... sinkhole_express.pyw`.

## [1.1.0] - 2026-08-17

### Added
- **Linux support.** The app now runs on modern Linux desktops (GNOME / KDE /
  XFCE) alongside Windows 11. Platform-specific changes:
  - `_set_window_icon()` uses `iconphoto()` with the PNG on Linux (was
    `iconbitmap()` with `.ico` — Windows-only).
  - `install_dependencies.sh` installs `python3-tk` via the system package
    manager (apt / dnf / pacman / zypper) and pip packages via `pip --user`.
  - `sinkhole-express.desktop` for Linux desktop integration.
  - Config stored at `~/.config/SinkholeExpress/config.json` on Linux
    (was already handled by the `APPDATA` fallback).
  - Password storage uses the Secret Service API (`gnome-keyring` / `kwallet`)
    via `keyring` on Linux.
- **Linux AppImage builds** in CI. The Release workflow now produces both
  `SinkholeExpress.exe` (Windows) and `SinkholeExpress-x86_64.AppImage` (Linux)
  on every tag push.

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

[Unreleased]: https://github.com/stavros-it/sinkhole-express/compare/v1.1.1...HEAD
[1.1.1]: https://github.com/stavros-it/sinkhole-express/releases/tag/v1.1.1
[1.1.0]: https://github.com/stavros-it/sinkhole-express/releases/tag/v1.1.0
[1.0.0]: https://github.com/stavros-it/sinkhole-express/releases/tag/v1.0.0
