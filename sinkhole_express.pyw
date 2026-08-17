#!/usr/bin/env python3
"""
Sinkhole Express (Tkinter edition)
----------------------------------
Tkinter GUI to view and toggle Pi-hole v6 blocking ON/OFF via its REST API.
On launch it authenticates and shows the current blocking status.

Host, port and HTTPS settings are editable in the GUI and saved to a small
config file (%APPDATA%\\SinkholeExpress\\config.json). The app password is stored
securely in the Windows Credential Manager (via `keyring`) and shown masked.

Launch on Windows 11 by double-clicking the .pyw file (no console window).

Requires: pip install keyring
Pi-hole v6 app password: Settings > Web interface / API > App password.
"""

import os
import json
import threading
import tkinter as tk
from tkinter import ttk, messagebox
import urllib.request
import urllib.error
import ssl

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
            # Pi-hole returns JSON error bodies; surface them.
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


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        cfg = load_config()
        self.api = None
        self.current = None  # True=enabled, False=disabled, None=unknown

        self.title("Sinkhole Express")
        self.geometry("360x430")
        self.resizable(False, False)
        self.configure(bg="#1e1e1e")
        try:
            _ico = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "sinkhole_express.ico")
            if os.path.exists(_ico):
                self.iconbitmap(_ico)
        except Exception:
            pass

        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("TButton", font=("Segoe UI", 10), padding=6)

        # High-visibility colored styles for the toggle button.
        # "Disable" (blocking currently ON)  -> red
        # "Enable"  (blocking currently OFF) -> green
        style.configure("Disable.TButton", font=("Segoe UI", 10, "bold"),
                        padding=8, foreground="#ffffff", background="#d32f2f")
        style.map("Disable.TButton",
                  background=[("active", "#b71c1c"), ("disabled", "#5a3535")],
                  foreground=[("disabled", "#bbbbbb")])
        style.configure("Enable.TButton", font=("Segoe UI", 10, "bold"),
                        padding=8, foreground="#ffffff", background="#2e7d32")
        style.map("Enable.TButton",
                  background=[("active", "#1b5e20"), ("disabled", "#35503a")],
                  foreground=[("disabled", "#bbbbbb")])

        tk.Label(self, text="Sinkhole Blocking", font=("Segoe UI", 14, "bold"),
                 bg="#1e1e1e", fg="#ffffff").pack(pady=(12, 2))

        self.status_lbl = tk.Label(self, text="Idle",
                                    font=("Segoe UI", 12, "bold"),
                                    bg="#1e1e1e", fg="#cccccc")
        self.status_lbl.pack(pady=8)

        self.toggle_btn = ttk.Button(self, text="Toggle", command=self.on_toggle,
                                     state="disabled")
        self.toggle_btn.pack(pady=3)

        self.refresh_btn = ttk.Button(self, text="Refresh", command=self.connect)
        self.refresh_btn.pack(pady=2)

        # -- Connection settings --
        conn = tk.Frame(self, bg="#1e1e1e")
        conn.pack(pady=(14, 4), padx=16, fill="x")

        row1 = tk.Frame(conn, bg="#1e1e1e")
        row1.pack(fill="x", pady=2)
        tk.Label(row1, text="Pi-hole IP / host", font=("Segoe UI", 9),
                 bg="#1e1e1e", fg="#aaaaaa", width=14, anchor="w").pack(side="left")
        self.host_var = tk.StringVar(value=str(cfg["host"]))
        ttk.Entry(row1, textvariable=self.host_var).pack(side="left",
                                                         fill="x", expand=True)

        row2 = tk.Frame(conn, bg="#1e1e1e")
        row2.pack(fill="x", pady=2)
        tk.Label(row2, text="Port", font=("Segoe UI", 9),
                 bg="#1e1e1e", fg="#aaaaaa", width=14, anchor="w").pack(side="left")
        self.port_var = tk.StringVar(value=str(cfg["port"]))
        ttk.Entry(row2, textvariable=self.port_var, width=8).pack(side="left")
        self.https_var = tk.BooleanVar(value=bool(cfg["https"]))
        ttk.Checkbutton(row2, text="HTTPS", variable=self.https_var,
                        command=self._on_https_toggle).pack(
            side="left", padx=(10, 0))

        # -- App password (masked) --
        row3 = tk.Frame(conn, bg="#1e1e1e")
        row3.pack(fill="x", pady=(6, 2))
        tk.Label(row3, text="App password", font=("Segoe UI", 9),
                 bg="#1e1e1e", fg="#aaaaaa", width=14, anchor="w").pack(side="left")
        self.pw_var = tk.StringVar(value=load_password())
        self.pw_entry = ttk.Entry(row3, textvariable=self.pw_var, show="•")
        self.pw_entry.pack(side="left", fill="x", expand=True)
        self.show_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(row3, text="Show", variable=self.show_var,
                        command=self._toggle_mask).pack(side="left", padx=(6, 0))

        btn_row = tk.Frame(conn, bg="#1e1e1e")
        btn_row.pack(fill="x", pady=(8, 0))
        ttk.Button(btn_row, text="Save & Connect",
                   command=self.save_and_connect).pack(side="left", expand=True,
                                                       fill="x", padx=(0, 3))
        ttk.Button(btn_row, text="Clear stored",
                   command=self.clear_stored).pack(side="left", expand=True,
                                                   fill="x", padx=(3, 0))

        # Auto-connect on launch if a password is already stored
        if self.pw_var.get():
            self.after(200, self.connect)
        else:
            self.status_lbl.config(text="Enter settings", fg="#e0a030")

    def _toggle_mask(self):
        self.pw_entry.config(show="" if self.show_var.get() else "•")

    def _on_https_toggle(self):
        """When switching scheme, nudge the port to the common default
        (Pi-hole v6 uses 8443 for HTTPS, 80 for HTTP) if the field still
        holds the other scheme's default."""
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

    # -- threaded helpers so the GUI never freezes --
    def _run(self, fn, on_done):
        def worker():
            try:
                result = fn()
            except Exception as exc:
                self.after(0, lambda err=exc: on_done(None, err))
            else:
                self.after(0, lambda res=result: on_done(res, None))
        threading.Thread(target=worker, daemon=True).start()

    def _validate(self):
        host = self.host_var.get().strip()
        port = self.port_var.get().strip()
        pw = self.pw_var.get().strip()
        if not host:
            self.status_lbl.config(text="Enter host/IP", fg="#e0a030")
            return None
        if not port.isdigit() or not (0 < int(port) < 65536):
            self.status_lbl.config(text="Invalid port", fg="#e0a030")
            return None
        if not pw:
            self.status_lbl.config(text="Enter app password", fg="#e0a030")
            return None
        return pw

    def connect(self):
        pw = self._validate()
        if pw is None:
            return
        self.api = PiHoleAPI(self._build_base_url())
        self.status_lbl.config(text="Authenticating...", fg="#cccccc")
        self.toggle_btn.config(state="disabled")
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
        self.toggle_btn.config(state="disabled")
        self.status_lbl.config(text="Stored password cleared", fg="#e0a030")

    def on_toggle(self):
        if self.current is None or self.api is None:
            return
        new_state = not self.current
        self.toggle_btn.config(state="disabled")
        self.status_lbl.config(text="Updating...", fg="#cccccc")
        self._run(lambda: (self.api.set_blocking(new_state),
                           self.api.get_status())[1], self._on_status)

    def _on_status(self, status, err):
        if err is not None:
            self.status_lbl.config(text="Error", fg="#e05555")
            self.toggle_btn.config(state="disabled")
            messagebox.showerror("Pi-hole Error", str(err))
            return

        if status == "enabled":
            self.current = True
            self.status_lbl.config(text="● ENABLED", fg="#4caf50")
            # Blocking is ON -> button turns it OFF: red
            self.toggle_btn.config(text="■  Disable Blocking",
                                   style="Disable.TButton", state="normal")
        elif status == "disabled":
            self.current = False
            self.status_lbl.config(text="● DISABLED", fg="#e0a030")
            # Blocking is OFF -> button turns it ON: green
            self.toggle_btn.config(text="▶  Enable Blocking",
                                   style="Enable.TButton", state="normal")
        else:
            self.current = None
            self.status_lbl.config(text=f"Unknown: {status}", fg="#cccccc")
            self.toggle_btn.config(state="disabled")

    def destroy(self):
        if self.api:
            self.api.logout()
        super().destroy()


if __name__ == "__main__":
    App().mainloop()
