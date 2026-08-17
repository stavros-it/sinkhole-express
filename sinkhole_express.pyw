#!/usr/bin/env python3
"""
Sinkhole Express
----------------
Modern-themed GUI to view and toggle Pi-hole v6 blocking ON/OFF via its
REST API. On launch it authenticates and shows the current blocking status.

Host, port and HTTPS settings are editable in the GUI and saved to a small
config file (%APPDATA%\\SinkholeExpress\\config.json). The app password is stored
securely in the Windows Credential Manager (via `keyring`) and shown masked.

Launch on Windows 11 by double-clicking the .pyw file (no console window).

Requires: pip install customtkinter keyring
Pi-hole v6 app password: Settings > Web interface / API > App password.
"""

import os
import json
import threading
import urllib.request
import urllib.error
import ssl

import customtkinter as ctk
from tkinter import messagebox
import keyring

# ---------------------------------------------------------------------------
# Defaults (used only until you save your own settings in the GUI)
# ---------------------------------------------------------------------------
DEFAULT_HOST = "192.168.1.10"
DEFAULT_PORT = 80
DEFAULT_HTTPS = False
VERIFY_TLS = False   # set True if using a valid cert over HTTPS
# ---------------------------------------------------------------------------

# Windows Credential Manager entry identifiers
CRED_SERVICE = "SinkholeExpress"
CRED_ACCOUNT = "app_password"

# Config file location (%APPDATA% on Windows, ~/.config elsewhere)
_APPDATA = os.environ.get("APPDATA") or os.path.expanduser("~/.config")
CONFIG_DIR = os.path.join(_APPDATA, "SinkholeExpress")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")


def load_config():
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        data = {}
    return {
        "host": data.get("host", DEFAULT_HOST),
        "port": data.get("port", DEFAULT_PORT),
        "https": data.get("https", DEFAULT_HTTPS),
    }


def save_config(host, port, https):
    try:
        os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump({"host": host, "port": port, "https": https}, f)
    except Exception:
        pass


def load_password():
    try:
        return keyring.get_password(CRED_SERVICE, CRED_ACCOUNT) or ""
    except Exception:
        return ""


def save_password(pw):
    keyring.set_password(CRED_SERVICE, CRED_ACCOUNT, pw)


def delete_password():
    try:
        keyring.delete_password(CRED_SERVICE, CRED_ACCOUNT)
    except Exception:
        pass


def make_tls_context():
    ctx = ssl.create_default_context()
    if not VERIFY_TLS:
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    return ctx


class PiHoleAPI:
    """Minimal Pi-hole v6 API client (session-based auth)."""

    def __init__(self, base_url):
        self.base_url = base_url
        self.sid = None
        self.ctx = make_tls_context()

    def _request(self, method, path, body=None, timeout=10, raw=False):
        url = f"{self.base_url}{path}"
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(url, data=data, method=method)
        req.add_header("Content-Type", "application/json")
        if self.sid:
            req.add_header("X-FTL-SID", self.sid)
        try:
            with urllib.request.urlopen(req, context=self.ctx,
                                        timeout=timeout) as resp:
                text = resp.read().decode()
                if raw:
                    return text
                return json.loads(text) if text else {}
        except urllib.error.HTTPError as e:
            detail = ""
            try:
                detail = json.loads(e.read().decode()).get(
                    "error", {}).get("message", "")
            except Exception:
                pass
            raise RuntimeError(f"HTTP {e.code}: {detail or e.reason}")
        except urllib.error.URLError as e:
            reason = getattr(e, "reason", e)
            if isinstance(reason, ssl.SSLError):
                raise RuntimeError(
                    f"TLS error: {reason}. If Pi-hole isn't using HTTPS, "
                    "untick HTTPS and use the HTTP port.")
            raise RuntimeError(
                f"Cannot reach {self.base_url} - {reason}. "
                "Check IP, port and HTTP/HTTPS setting.")

    def authenticate(self, password):
        result = self._request("POST", "/auth", {"password": password})
        session = result.get("session", {})
        if not session.get("valid"):
            raise RuntimeError("Authentication failed - check app password.")
        self.sid = session.get("sid")
        return self.sid

    def get_status(self):
        result = self._request("GET", "/dns/blocking")
        return result.get("blocking")

    def get_stats(self):
        """Return the summary stats dict (queries, clients, gravity)."""
        return self._request("GET", "/stats/summary")

    def set_blocking(self, enabled, timer=None):
        body = {"blocking": bool(enabled), "timer": timer}
        return self._request("POST", "/dns/blocking", body)

    def update_gravity(self):
        """Trigger a gravity (blocklist) update. This streams a plain-text
        progress log (NOT JSON) and can take 20-60s, so use a long timeout."""
        return self._request("POST", "/action/gravity", timeout=180, raw=True)

    def get_version(self):
        """Return version info dict for core/web/ftl (local + remote)."""
        return self._request("GET", "/info/version")

    def logout(self):
        if self.sid:
            try:
                self._request("DELETE", "/auth")
            except Exception:
                pass
            self.sid = None


ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


def _set_window_icon(win):
    """Set the titlebar/taskbar icon from the bundled .ico if present."""
    try:
        ico = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "sinkhole_express.ico")
        if os.path.exists(ico):
            win.iconbitmap(ico)
    except Exception:
        pass


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        cfg = load_config()
        self.api = None
        self.current = None  # True=enabled, False=disabled, None=unknown

        self.title("Sinkhole Express")
        self.geometry("380x700")
        self.resizable(False, False)
        _set_window_icon(self)

        # ---- Header ----
        ctk.CTkLabel(self, text="Sinkhole Blocking",
                     font=ctk.CTkFont(size=20, weight="bold")).pack(pady=(18, 2))

        # Gear button pinned to the top-right corner (always visible)
        self.gear_btn = ctk.CTkButton(
            self, text="⚙", width=36, height=36, corner_radius=8,
            font=ctk.CTkFont(size=18), command=self.open_settings)
        self.gear_btn.place(relx=1.0, x=-14, y=14, anchor="ne")

        self.status_lbl = ctk.CTkLabel(
            self, text="Idle", font=ctk.CTkFont(size=15, weight="bold"),
            text_color="#cccccc")
        self.status_lbl.pack(pady=10)

        # ---- Toggle button (colored, high visibility) ----
        self.toggle_btn = ctk.CTkButton(
            self, text="Toggle", command=self.on_toggle, state="disabled",
            height=44, font=ctk.CTkFont(size=14, weight="bold"),
            corner_radius=10)
        self.toggle_btn.pack(pady=6, padx=24, fill="x")

        # ---- Secondary actions row: Refresh + Update Gravity ----
        sec_row = ctk.CTkFrame(self, fg_color="transparent")
        sec_row.pack(pady=(0, 6), padx=24, fill="x")
        self.refresh_btn = ctk.CTkButton(
            sec_row, text="Refresh", command=self.refresh, height=32,
            fg_color="transparent", border_width=1, corner_radius=10)
        self.refresh_btn.pack(side="left", expand=True, fill="x", padx=(0, 4))
        self.gravity_btn = ctk.CTkButton(
            sec_row, text="Update Gravity", command=self.on_update_gravity,
            height=32, corner_radius=10, fg_color="#3a6ea5",
            hover_color="#2f5a87", state="disabled")
        self.gravity_btn.pack(side="left", expand=True, fill="x", padx=(4, 0))

        # ---- Statistics panel (today's totals) ----
        stats = ctk.CTkFrame(self, corner_radius=12)
        stats.pack(pady=(4, 4), padx=16, fill="x")
        ctk.CTkLabel(stats, text="Statistics (today)",
                     font=ctk.CTkFont(size=12, weight="bold"),
                     text_color="#9aa0aa").pack(pady=(8, 4))

        grid = ctk.CTkFrame(stats, fg_color="transparent")
        grid.pack(padx=12, pady=(0, 10), fill="x")
        grid.grid_columnconfigure((0, 1), weight=1)

        # Each stat = (big value label, caption). Store value labels for updates.
        self.stat_vars = {}
        specs = [
            ("queries",   "Total queries",   "#5aa9e6"),
            ("blocked",   "Blocked",         "#e05555"),
            ("percent",   "% Blocked",       "#e0a030"),
            ("domains",   "Domains on list", "#4caf50"),
            ("clients",   "Active clients",  "#b58ce0"),
            ("cached",    "Cached",          "#5ac8b0"),
        ]
        for i, (key, caption, color) in enumerate(specs):
            r, c = divmod(i, 2)
            cell = ctk.CTkFrame(grid, corner_radius=8)
            cell.grid(row=r, column=c, padx=4, pady=4, sticky="nsew")
            val = ctk.CTkLabel(cell, text="—",
                               font=ctk.CTkFont(size=17, weight="bold"),
                               text_color=color)
            val.pack(pady=(8, 0))
            ctk.CTkLabel(cell, text=caption, font=ctk.CTkFont(size=10),
                         text_color="#8a909a").pack(pady=(0, 8))
            self.stat_vars[key] = val

        # ---- Version / update info ----
        ver = ctk.CTkFrame(self, corner_radius=12)
        ver.pack(pady=(4, 4), padx=16, fill="x")
        ctk.CTkLabel(ver, text="Pi-hole version",
                     font=ctk.CTkFont(size=12, weight="bold"),
                     text_color="#9aa0aa").pack(pady=(8, 2))
        self.version_lbl = ctk.CTkLabel(
            ver, text="—", font=ctk.CTkFont(size=12),
            text_color="#cfd3da")
        self.version_lbl.pack(pady=(0, 2))
        self.update_lbl = ctk.CTkLabel(
            ver, text="", font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#4caf50")
        self.update_lbl.pack(pady=(0, 8))

        # ---- Settings values (edited via the Settings window) ----
        self.host_var = ctk.StringVar(value=str(cfg["host"]))
        self.port_var = ctk.StringVar(value=str(cfg["port"]))
        self.https_var = ctk.BooleanVar(value=bool(cfg["https"]))
        self.pw_var = ctk.StringVar(value=load_password())
        self.show_var = ctk.BooleanVar(value=False)
        self._settings_win = None

        # ---- Bottom action row (anchored to bottom, always visible) ----
        action_row = ctk.CTkFrame(self, fg_color="transparent")
        action_row.pack(side="bottom", pady=(10, 16), padx=16, fill="x")
        ctk.CTkButton(action_row, text="⚙  Settings",
                      command=self.open_settings, height=40,
                      font=ctk.CTkFont(size=13, weight="bold"),
                      corner_radius=10).pack(
            side="left", expand=True, fill="x", padx=(0, 4))
        ctk.CTkButton(action_row, text="Reconnect", command=self.connect,
                      height=40, corner_radius=10, fg_color="transparent",
                      border_width=1).pack(
            side="left", expand=True, fill="x", padx=(4, 0))

        # Auto-connect on launch if a password is already stored
        if self.pw_var.get():
            self.after(200, self.connect)
        else:
            self.status_lbl.configure(text="Open Settings to configure",
                                      text_color="#e0a030")

    # ---- Settings window ----
    def open_settings(self):
        # Bring existing window to front if already open
        if self._settings_win is not None and self._settings_win.winfo_exists():
            self._settings_win.focus()
            self._settings_win.lift()
            return

        win = ctk.CTkToplevel(self)
        self._settings_win = win
        win.title("Settings")
        win.geometry("360x360")
        win.resizable(False, False)
        win.transient(self)
        # Re-apply icon shortly after creation (Toplevel timing quirk)
        win.after(200, lambda: _set_window_icon(win))

        ctk.CTkLabel(win, text="Connection settings",
                     font=ctk.CTkFont(size=15, weight="bold")).pack(pady=(16, 8))

        frame = ctk.CTkFrame(win, corner_radius=12)
        frame.pack(padx=16, pady=(0, 12), fill="both", expand=True)

        ctk.CTkLabel(frame, text="Pi-hole IP / host",
                     anchor="w").pack(fill="x", padx=14, pady=(14, 0))
        ctk.CTkEntry(frame, textvariable=self.host_var).pack(
            fill="x", padx=14, pady=(2, 8))

        port_row = ctk.CTkFrame(frame, fg_color="transparent")
        port_row.pack(fill="x", padx=14)
        port_col = ctk.CTkFrame(port_row, fg_color="transparent")
        port_col.pack(side="left")
        ctk.CTkLabel(port_col, text="Port", anchor="w").pack(fill="x")
        ctk.CTkEntry(port_col, textvariable=self.port_var, width=90).pack()
        ctk.CTkSwitch(port_row, text="HTTPS", variable=self.https_var,
                      command=self._on_https_toggle).pack(
            side="left", padx=(18, 0), pady=(18, 0))

        ctk.CTkLabel(frame, text="App password (API)",
                     anchor="w").pack(fill="x", padx=14, pady=(12, 0))
        pw_row = ctk.CTkFrame(frame, fg_color="transparent")
        pw_row.pack(fill="x", padx=14, pady=(2, 8))
        self.pw_entry = ctk.CTkEntry(pw_row, textvariable=self.pw_var, show="•")
        self.pw_entry.pack(side="left", fill="x", expand=True)
        self.show_var.set(False)
        ctk.CTkCheckBox(pw_row, text="Show", variable=self.show_var,
                        width=60, command=self._toggle_mask).pack(
            side="left", padx=(8, 0))

        btn_row = ctk.CTkFrame(frame, fg_color="transparent")
        btn_row.pack(fill="x", padx=14, pady=(6, 14))

        def save_close():
            if self.save_and_connect():
                win.destroy()

        ctk.CTkButton(btn_row, text="Save & Connect",
                      command=save_close).pack(
            side="left", expand=True, fill="x", padx=(0, 4))
        ctk.CTkButton(btn_row, text="Clear stored", command=self.clear_stored,
                      fg_color="transparent", border_width=1).pack(
            side="left", expand=True, fill="x", padx=(4, 0))

        def on_close():
            self._settings_win = None
            win.destroy()
        win.protocol("WM_DELETE_WINDOW", on_close)

    # ---- UI helpers ----
    def _toggle_mask(self):
        self.pw_entry.configure(show="" if self.show_var.get() else "•")

    def _on_https_toggle(self):
        """Nudge the port to the common default when switching scheme."""
        port = self.port_var.get().strip()
        if self.https_var.get():
            if port in ("", "80", "82", "8080"):
                self.port_var.set("443")
        else:
            if port in ("", "443", "8443"):
                self.port_var.set("80")

    def _build_base_url(self):
        host = self.host_var.get().strip()
        port = self.port_var.get().strip()
        scheme = "https" if self.https_var.get() else "http"
        return f"{scheme}://{host}:{port}/api"

    # ---- threaded helpers ----
    def _run(self, fn, on_done):
        def worker():
            try:
                result = fn()
            except Exception as exc:
                # Bind the exception to a default arg so the scheduled callback
                # keeps a reference (Python deletes 'except' vars on block exit).
                self.after(0, lambda err=exc: on_done(None, err))
            else:
                self.after(0, lambda res=result: on_done(res, None))
        threading.Thread(target=worker, daemon=True).start()

    def _validate(self):
        host = self.host_var.get().strip()
        port = self.port_var.get().strip()
        pw = self.pw_var.get().strip()
        msg = None
        if not host:
            msg = "Enter a host/IP."
        elif not port.isdigit() or not (0 < int(port) < 65536):
            msg = "Port must be a number between 1 and 65535."
        elif not pw:
            msg = "Enter the app password."
        if msg:
            self.status_lbl.configure(text="Check settings", text_color="#e0a030")
            messagebox.showwarning("Settings", msg)
            return None
        return pw

    # ---- actions ----
    def connect(self):
        pw = self._validate()
        if pw is None:
            return
        self.api = PiHoleAPI(self._build_base_url())
        self.status_lbl.configure(text="Authenticating...", text_color="#cccccc")
        self.toggle_btn.configure(state="disabled")

        def task():
            self.api.authenticate(pw)
            status = self.api.get_status()
            stats = None
            version = None
            try:
                stats = self.api.get_stats()
            except Exception:
                pass  # stats are non-critical
            try:
                version = self.api.get_version()
            except Exception:
                pass  # version is non-critical
            return (status, stats, version)

        self._run(task, self._on_status)

    def refresh(self):
        """Re-read status + stats using the EXISTING session (no re-auth).
        Falls back to a full connect if there is no session yet."""
        if self.api is None or self.api.sid is None:
            self.connect()
            return

        self.status_lbl.configure(text="Refreshing...", text_color="#cccccc")

        def task():
            status = self.api.get_status()
            stats = None
            version = None
            try:
                stats = self.api.get_stats()
            except Exception:
                pass
            try:
                version = self.api.get_version()
            except Exception:
                pass
            return (status, stats, version)

        self._run(task, self._on_refresh)

    def _on_refresh(self, result, err):
        # If the session expired (e.g. 401), transparently re-authenticate once.
        if err is not None:
            msg = str(err)
            if "401" in msg or "unauthor" in msg.lower():
                self.connect()
                return
        self._on_status(result, err)

    def save_and_connect(self):
        pw = self._validate()
        if pw is None:
            return False
        save_config(self.host_var.get().strip(),
                    int(self.port_var.get().strip()),
                    bool(self.https_var.get()))
        try:
            save_password(pw)
        except Exception as e:
            messagebox.showerror("Credential store", str(e))
            return False
        self.connect()
        return True

    def clear_stored(self):
        delete_password()
        self.pw_var.set("")
        if self.api:
            self.api.logout()
        self.current = None
        self.toggle_btn.configure(state="disabled")
        self.status_lbl.configure(text="Stored password cleared",
                                  text_color="#e0a030")

    def on_toggle(self):
        if self.current is None or self.api is None:
            return
        new_state = not self.current
        self.toggle_btn.configure(state="disabled")
        self.status_lbl.configure(text="Updating...", text_color="#cccccc")

        def task():
            self.api.set_blocking(new_state)
            status = self.api.get_status()
            stats = None
            version = None
            try:
                stats = self.api.get_stats()
            except Exception:
                pass
            try:
                version = self.api.get_version()
            except Exception:
                pass
            return (status, stats, version)

        self._run(task, self._on_status)

    def _fmt(self, n):
        """Human-friendly integer formatting with thousands separators."""
        try:
            return f"{int(n):,}"
        except (TypeError, ValueError):
            return "—"

    def _update_stats(self, stats):
        if not stats:
            return
        q = stats.get("queries", {}) or {}
        clients = stats.get("clients", {}) or {}
        gravity = stats.get("gravity", {}) or {}
        pct = q.get("percent_blocked")
        self.stat_vars["queries"].configure(text=self._fmt(q.get("total")))
        self.stat_vars["blocked"].configure(text=self._fmt(q.get("blocked")))
        self.stat_vars["percent"].configure(
            text=f"{pct:.1f}%" if isinstance(pct, (int, float)) else "—")
        self.stat_vars["domains"].configure(
            text=self._fmt(gravity.get("domains_being_blocked")))
        self.stat_vars["clients"].configure(text=self._fmt(clients.get("active")))
        self.stat_vars["cached"].configure(text=self._fmt(q.get("cached")))

    def _update_version(self, version):
        """Show core/web/FTL versions and flag if any update is available.
        The /info/version payload nests local/remote under version.<component>."""
        if not version:
            return
        data = version.get("version", version) or {}
        parts = []
        update_available = False
        for comp in ("core", "web", "ftl"):
            c = data.get(comp) or {}
            local = (c.get("local") or {}).get("version")
            remote = (c.get("remote") or {}).get("version")
            if local:
                parts.append(f"{comp.upper()} {local}")
            # remote newer than local => update available
            if local and remote and remote != local:
                update_available = True

        self.version_lbl.configure(
            text="   ".join(parts) if parts else "unknown")

        if update_available:
            self.update_lbl.configure(
                text="⬆ Update available (run: pihole -up on the Pi)",
                text_color="#e0a030")
        else:
            self.update_lbl.configure(text="✓ Up to date",
                                      text_color="#4caf50")

    # ---- gravity update ----
    def on_update_gravity(self):
        if self.api is None or self.api.sid is None:
            messagebox.showinfo("Update Gravity", "Connect first.")
            return
        if not messagebox.askyesno(
                "Update Gravity",
                "Re-download and rebuild all blocklists now?\n"
                "This can take up to a minute."):
            return

        self.gravity_btn.configure(state="disabled", text="Updating…")
        self.refresh_btn.configure(state="disabled")
        self.status_lbl.configure(text="Updating gravity…", text_color="#cccccc")

        self._run(self.api.update_gravity, self._on_gravity_done)

    def _on_gravity_done(self, result, err):
        self.gravity_btn.configure(state="normal", text="Update Gravity")
        self.refresh_btn.configure(state="normal")
        if err is not None:
            self.status_lbl.configure(text="Gravity update failed",
                                      text_color="#e05555")
            messagebox.showerror("Update Gravity", str(err))
            return
        self.status_lbl.configure(text="Gravity updated ✓",
                                  text_color="#4caf50")
        # Refresh stats so the new blocklist size shows
        self.after(300, self.refresh)

    def _on_status(self, result, err):
        if err is not None:
            self.status_lbl.configure(text="Error", text_color="#e05555")
            self.toggle_btn.configure(state="disabled")
            messagebox.showerror("Pi-hole Error", str(err))
            return

        status, stats, version = result
        self._update_stats(stats)
        self._update_version(version)
        # Gravity update is available once we have a working session
        self.gravity_btn.configure(state="normal")

        if status == "enabled":
            self.current = True
            self.status_lbl.configure(text="● ENABLED", text_color="#4caf50")
            # Blocking ON -> button turns it OFF: red
            self.toggle_btn.configure(
                text="■  Disable Blocking", state="normal",
                fg_color="#d32f2f", hover_color="#b71c1c")
        elif status == "disabled":
            self.current = False
            self.status_lbl.configure(text="● DISABLED", text_color="#e0a030")
            # Blocking OFF -> button turns it ON: green
            self.toggle_btn.configure(
                text="▶  Enable Blocking", state="normal",
                fg_color="#2e7d32", hover_color="#1b5e20")
        else:
            self.current = None
            self.status_lbl.configure(text=f"Unknown: {status}",
                                      text_color="#cccccc")
            self.toggle_btn.configure(state="disabled")

    def destroy(self):
        if self.api:
            self.api.logout()
        super().destroy()


if __name__ == "__main__":
    App().mainloop()
