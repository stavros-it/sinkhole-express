# Sinkhole Express

<p align="center">
  <img src="sinkhole_express_icon.png" alt="Sinkhole Express" width="128" height="128">
</p>

<p align="center">
  Lightweight desktop utility to view and toggle
  <a href="https://pi-hole.net/">Pi-hole</a> v6 DNS blocking ON/OFF,
  with live stats and gravity updates — without opening the Pi-hole web admin.
  Runs on Windows 11 and Linux.
</p>

<p align="center">
  <a href="https://github.com/stavros-it/sinkhole-express/actions/workflows/ci.yml"><img alt="CI" src="https://github.com/stavros-it/sinkhole-express/actions/workflows/ci.yml/badge.svg"></a>
  <a href="https://github.com/stavros-it/sinkhole-express/actions/workflows/release.yml"><img alt="Release" src="https://github.com/stavros-it/sinkhole-express/actions/workflows/release.yml/badge.svg"></a>
  <a href="https://github.com/stavros-it/sinkhole-express/releases"><img alt="platform" src="https://img.shields.io/badge/platform-Windows%2011%20%7C%20Linux-blue"></a>
  <a href="https://www.python.org/downloads/"><img alt="python" src="https://img.shields.io/badge/python-3.12%2B-blue"></a>
  <a href="https://docs.pi-hole.net/main/ftldns/"><img alt="pi--hole" src="https://img.shields.io/badge/Pi--hole-v6%20REST%20API-green"></a>
  <a href="https://github.com/stavros-it/sinkhole-express/stargazers"><img alt="stars" src="https://img.shields.io/github/stars/stavros-it/sinkhole-express?style=social"></a>
</p>

---

## Features

- **One-click toggle** of Pi-hole v6 DNS blocking (ON / OFF).
- **Live status indicator** — green `● ENABLED` / amber `● DISABLED`, with color-coded toggle button.
- **Statistics panel** — total queries, blocked, % blocked, domains on list, active clients, cached (today's totals).
- **Pi-hole version panel** — shows CORE / WEB / FTL versions and flags when an update is available.
- **Update Gravity** button — re-downloads and rebuilds blocklists (`pihole -g`) via the API.
- **Settings window** — host, port, HTTPS toggle, masked app password (stored securely via `keyring`).
- **Windowless launch** — `.pyw` + `pythonw.exe` (Windows) or `python3` (Linux), no console window.
- **Auto-connect on launch** when credentials are already stored.
- Built with [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter) for a modern, dark UI.

## Screenshots

<table align="center">
  <tr>
    <td align="center"><img src="screenshots/enabled.png" alt="Blocking enabled" width="320"></td>
    <td align="center"><img src="screenshots/disabled.png" alt="Blocking disabled" width="320"></td>
  </tr>
  <tr>
    <td align="center"><strong>Blocking enabled</strong></td>
    <td align="center"><strong>Blocking disabled</strong></td>
  </tr>
</table>

## Requirements

- **OS:** Windows 11 or a modern Linux desktop (GNOME, KDE, XFCE, etc.).
- **Python:** 3.12+
  - **Windows:** from [python.org](https://www.python.org/downloads/). Make sure **"Add python.exe to PATH"** is checked during install.
  - **Linux:** your distro's `python3` package. Also install `python3-tk` (ships separately on most distros) — the install script handles this.
- **Pi-hole:** v6.x with the REST API enabled (not the legacy v5 `api.php`).
- **App password:** in Pi-hole web admin → *Settings → Web interface / API → App password*.
- **Linux only:** a Secret Service provider (`gnome-keyring` or `kwallet`) for password storage. Most desktop environments include one by default.

## Installation

### Option A — Download a prebuilt binary (recommended)

Grab the latest release from the [Releases page](https://github.com/stavros-it/sinkhole-express/releases):

- **Windows:** download `SinkholeExpress.exe` and double-click.
  > ⚠️ **SmartScreen warning:** because the `.exe` is not code-signed (this is a
  > free, open-source project), Microsoft Defender SmartScreen may show
  > *"Windows protected your PC"* or *"isn't commonly downloaded"*. This is
  > expected. Click **More info** → **Run anyway** to launch the app. The file
  > is built directly from the source in this repo by GitHub Actions — you can
  > verify the build log on the Actions tab.
- **Linux:** download `SinkholeExpress-x86_64.AppImage`, make it executable, and run:
  ```bash
  chmod +x SinkholeExpress-x86_64.AppImage
  ./SinkholeExpress-x86_64.AppImage
  ```

### Option B — Run from source

1. Clone the repo:
   ```bash
   git clone https://github.com/stavros-it/sinkhole-express.git
   cd sinkhole-express
   ```
2. Install Python dependencies:

   **Windows:**
   ```bat
   install_dependencies.bat
   ```
   Installs `keyring` (Credential Manager access) and `customtkinter` (modern UI).

   **Linux:**
   ```bash
   chmod +x install_dependencies.sh
   ./install_dependencies.sh
   ```
   Installs `python3-tk` via your package manager, then `customtkinter` and `keyring` via pip.

3. *(Optional, Windows only)* Create a desktop shortcut:
   ```bat
   create_desktop_shortcut.bat
   ```
   Creates a **"Sinkhole Express"** desktop shortcut that launches via `pythonw.exe` with the bundled `.ico`.

4. Run the app:
   ```bash
   python3 sinkhole_express.pyw
   ```

## Usage

1. Launch `sinkhole_express.pyw` (double-click it, or use the desktop shortcut).
2. On first run it will say *"Open Settings to configure"* — click the **⚙ Settings** button (top-right).
3. Enter:
   - **Pi-hole IP / host** — e.g. `192.168.1.10`
   - **Port** — Pi-hole v6 defaults: `80` for HTTP, `443` for HTTPS (but check `sudo pihole-FTL --config webserver.port` — see *Port gotcha* below).
   - **HTTPS** — tick if your Pi-hole uses TLS.
   - **App password** — from Pi-hole web admin → *Settings → Web interface / API → App password*.
4. Click **Save & Connect**. The app authenticates, fetches status + stats, and the toggle becomes active.

From the main window you can:
- Click the big red/green button to **toggle blocking**.
- Click **Refresh** to re-read status + stats (no re-auth).
- Click **Update Gravity** to rebuild blocklists (takes 20–60 s).
- Click **⚙ Settings** (bottom) to edit connection / change password, or **Clear stored** to wipe the saved password.

## How it works

Sinkhole Express talks to the Pi-hole v6 REST API (`pihole-FTL`) directly:

| Action | HTTP | Endpoint |
|--------|------|----------|
| Authenticate | `POST` | `/api/auth` (returns `session.sid`) |
| Read status | `GET` | `/api/dns/blocking` |
| Toggle blocking | `POST` | `/api/dns/blocking` (`{blocking, timer}`) |
| Stats | `GET` | `/api/stats/summary` |
| Version info | `GET` | `/api/info/version` |
| Update gravity | `POST` | `/api/action/gravity` (streams plain-text progress) |
| Logout | `DELETE` | `/api/auth` |

All network calls run on a background thread (`threading.Thread(daemon=True)`) and results are marshalled back to the UI via `after(0, …)` so the window never freezes.

### Port gotcha (important)

Pi-hole v6 default HTTPS port is **8443**, NOT `443`. But installations vary widely (e.g. `82o,443os` means HTTP on 80/82, HTTPS on 443/8443). To check the real ports on your Pi:

```bash
sudo pihole-FTL --config webserver.port
```

Output suffix flags: `o` = redirect, `s` = TLS. Sinkhole Express auto-suggests 80/443 when you flip the HTTPS switch, but only when the field still holds the other scheme's default — manual overrides are preserved.

## Configuration & security

Two separate stores — **the password is never written to disk in plaintext**.

1. **Connection settings** → JSON file
   - Windows: `%APPDATA%\SinkholeExpress\config.json`
   - Linux: `~/.config/SinkholeExpress/config.json`
   - Keys: `host`, `port`, `https`.
2. **App password** → OS credential store (via `keyring`)
   - Windows: Windows Credential Manager.
   - Linux: Secret Service (`gnome-keyring` / `kwallet`).
   - Service name: `SinkholeExpress`, account: `app_password`.
   - ⚠️ Any process running as the same user can read this back. Acceptable for a personal workstation; bear it in mind for shared machines.

## Project structure

| File | Role |
|------|------|
| `sinkhole_express.pyw` | Main app — CustomTkinter UI |
| `sinkhole_express.ico` | Multi-res Windows icon (256→16 px) |
| `sinkhole_express_icon.png` | 512 px PNG preview / Linux icon |
| `install_dependencies.bat` | Installs deps on Windows |
| `install_dependencies.sh` | Installs deps on Linux |
| `create_desktop_shortcut.bat` | Creates the desktop shortcut (Windows) |
| `sinkhole-express.desktop` | Linux desktop entry file |
| `PROJECT_CONTEXT.md` | Architecture / endpoints reference for AI coding agents |

## Building from source

Prebuilt binaries are produced by CI on every release tag. To build locally:

**Windows (.exe):**
```bat
pip install pyinstaller
pyinstaller --onefile --windowed --icon sinkhole_express.ico --name "SinkholeExpress" --add-data "sinkhole_express.ico;." --add-data "sinkhole_express_icon.png;." --collect-data customtkinter sinkhole_express.pyw
```

**Linux (AppImage):**
```bash
pip install pyinstaller
pyinstaller --onefile --windowed --icon sinkhole_express.ico --name "SinkholeExpress" --add-data "sinkhole_express_icon.png:." --add-data "sinkhole_express.ico:." --collect-data customtkinter sinkhole_express.pyw
# Then wrap in an AppImage using appimagetool (see .github/workflows/release.yml for the full steps)
```

## Roadmap

- [ ] Timed auto-refresh of stats (e.g. every 10 s).
- [ ] Temporary-disable dropdown (5 / 10 / 30 min) wired to `set_blocking(timer=…)`.
- [ ] PyInstaller build script for a self-contained `.exe`.
- [ ] Greek-language HTML user guide.
- [ ] Multi-Pi-hole support (profiles / dropdown).

## License

Licensed under the **MIT License** — see [LICENSE](LICENSE).

"Pi-hole" is a trademark of Pi-hole, LLC; this project is independent and not affiliated with Pi-hole.

## Acknowledgements

- [Pi-hole](https://pi-hole.net/) — the upstream project whose v6 REST API this app drives.
- [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter) — the modern dark UI framework.
- [keyring](https://github.com/jaraco/keyring) — for secure credential storage in Windows Credential Manager.

## AI assistance

Parts of this codebase, documentation and commit messages were generated or refined with the help of AI tools. All output was reviewed and accepted by the maintainer before being committed.
