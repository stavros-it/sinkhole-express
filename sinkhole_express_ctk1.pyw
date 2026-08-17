#!/usr/bin/env python3
"""
Sinkhole Express (CustomTkinter edition)
---------------------------------------
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

    def _request(self, method, path, body=None):
        url = f"{self.base_url}{path}"
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(url, data=data, method=method)
        req.add_header("Content-Type", "application/json")
        if self.sid:
            req.add_header("X-FTL-SID", self.sid)
        try:
            with urllib.request.urlopen(req, context=self.ctx,
                                        timeout=10) as resp:
                raw = resp.read().decode()
                return json.loads(raw) if raw else {}
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

    def set_blocking(self, enabled, timer=None):
        body = {"blocking": bool(enabled), "timer": timer}
        return self._request("POST", "/dns/blocking", body)

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
        self.geometry("380x470")
        self.resizable(False, False)
        _set_window_icon(self)

        # ---- Header ----
        ctk.CTkLabel(self, text="Sinkhole Blocking",
                     font=ctk.CTkFont(size=20, weight="bold")).pack(pady=(18, 2))

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

        self.refresh_btn = ctk.CTkButton(
            self, text="Refresh", command=self.connect, height=32,
            fg_color="transparent", border_width=1, corner_radius=10)
        self.refresh_btn.pack(pady=(0, 6), padx=24, fill="x")

        # ---- Settings frame ----
        frame = ctk.CTkFrame(self, corner_radius=12)
        frame.pack(pady=(12, 16), padx=16, fill="both", expand=True)

        ctk.CTkLabel(frame, text="Pi-hole IP / host",
                     anchor="w").pack(fill="x", padx=14, pady=(14, 0))
        self.host_var = ctk.StringVar(value=str(cfg["host"]))
        ctk.CTkEntry(frame, textvariable=self.host_var).pack(
            fill="x", padx=14, pady=(2, 8))

        port_row = ctk.CTkFrame(frame, fg_color="transparent")
        port_row.pack(fill="x", padx=14)
        port_col = ctk.CTkFrame(port_row, fg_color="transparent")
        port_col.pack(side="left")
        ctk.CTkLabel(port_col, text="Port", anchor="w").pack(fill="x")
        self.port_var = ctk.StringVar(value=str(cfg["port"]))
        ctk.CTkEntry(port_col, textvariable=self.port_var, width=90).pack()
        self.https_var = ctk.BooleanVar(value=bool(cfg["https"]))
        ctk.CTkSwitch(port_row, text="HTTPS", variable=self.https_var,
                      command=self._on_https_toggle).pack(
            side="left", padx=(18, 0), pady=(18, 0))

        ctk.CTkLabel(frame, text="App password (API)",
                     anchor="w").pack(fill="x", padx=14, pady=(12, 0))
        pw_row = ctk.CTkFrame(frame, fg_color="transparent")
        pw_row.pack(fill="x", padx=14, pady=(2, 8))
        self.pw_var = ctk.StringVar(value=load_password())
        self.pw_entry = ctk.CTkEntry(pw_row, textvariable=self.pw_var, show="•")
        self.pw_entry.pack(side="left", fill="x", expand=True)
        self.show_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(pw_row, text="Show", variable=self.show_var,
                        width=60, command=self._toggle_mask).pack(
            side="left", padx=(8, 0))

        btn_row = ctk.CTkFrame(frame, fg_color="transparent")
        btn_row.pack(fill="x", padx=14, pady=(6, 14))
        ctk.CTkButton(btn_row, text="Save & Connect",
                      command=self.save_and_connect).pack(
            side="left", expand=True, fill="x", padx=(0, 4))
        ctk.CTkButton(btn_row, text="Clear stored", command=self.clear_stored,
                      fg_color="transparent", border_width=1).pack(
            side="left", expand=True, fill="x", padx=(4, 0))

        # Auto-connect on launch if a password is already stored
        if self.pw_var.get():
            self.after(200, self.connect)
        else:
            self.status_lbl.configure(text="Enter settings",
                                      text_color="#e0a030")

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
                self.after(0, lambda: on_done(result, None))
            except Exception as e:
                self.after(0, lambda: on_done(None, e))
        threading.Thread(target=worker, daemon=True).start()

    def _validate(self):
        host = self.host_var.get().strip()
        port = self.port_var.get().strip()
        pw = self.pw_var.get().strip()
        if not host:
            self.status_lbl.configure(text="Enter host/IP", text_color="#e0a030")
            return None
        if not port.isdigit() or not (0 < int(port) < 65536):
            self.status_lbl.configure(text="Invalid port", text_color="#e0a030")
            return None
        if not pw:
            self.status_lbl.configure(text="Enter app password",
                                      text_color="#e0a030")
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
        self._run(lambda: (self.api.authenticate(pw), self.api.get_status())[1],
                  self._on_status)

    def save_and_connect(self):
        pw = self._validate()
        if pw is None:
            return
        save_config(self.host_var.get().strip(),
                    int(self.port_var.get().strip()),
                    bool(self.https_var.get()))
        try:
            save_password(pw)
        except Exception as e:
            messagebox.showerror("Credential store", str(e))
            return
        self.connect()

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
        self._run(lambda: (self.api.set_blocking(new_state),
                           self.api.get_status())[1], self._on_status)

    def _on_status(self, status, err):
        if err is not None:
            self.status_lbl.configure(text="Error", text_color="#e05555")
            self.toggle_btn.configure(state="disabled")
            messagebox.showerror("Pi-hole Error", str(err))
            return

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
