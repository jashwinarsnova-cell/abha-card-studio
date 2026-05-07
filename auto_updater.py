# auto_updater.py
# ============================================================
#  ABHA Card Studio — Auto Updater
#  Place this file in your project root and call check_for_update()
#  at the start of your main app.
# ============================================================

import os
import sys
import json
import threading
import subprocess
import tempfile
import urllib.request
import urllib.error
import tkinter as tk
from tkinter import messagebox
from packaging import version  # pip install packaging

# ── CONFIG — update these two lines only ──────────────────────
GITHUB_USER    = "your-github-username"   # e.g. "john"
GITHUB_REPO    = "your-repo-name"         # e.g. "abha-card-studio"
CURRENT_VERSION = "5.2"                   # must match your AppVersion in .iss
# ─────────────────────────────────────────────────────────────

API_URL = f"https://api.github.com/repos/{GITHUB_USER}/{GITHUB_REPO}/releases/latest"


def get_latest_release():
    """Fetch latest release info from GitHub API."""
    req = urllib.request.Request(
        API_URL,
        headers={"User-Agent": "ABHA-Card-Studio-Updater"}
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode())


def find_installer_asset(release):
    """Find the .exe installer asset in the release."""
    for asset in release.get("assets", []):
        if asset["name"].endswith(".exe"):
            return asset["browser_download_url"], asset["name"]
    return None, None


def download_installer(url, filename, progress_callback=None):
    """Download installer to temp directory with optional progress callback."""
    tmp_dir  = tempfile.gettempdir()
    tmp_path = os.path.join(tmp_dir, filename)

    def reporthook(block_num, block_size, total_size):
        if progress_callback and total_size > 0:
            percent = min(100, block_num * block_size * 100 // total_size)
            progress_callback(percent)

    urllib.request.urlretrieve(url, tmp_path, reporthook)
    return tmp_path


def run_installer_and_exit(installer_path):
    """Launch the installer silently then close this app."""
    subprocess.Popen(
        [installer_path, "/SILENT", "/NORESTART"],
        creationflags=subprocess.DETACHED_PROCESS
    )
    sys.exit(0)


def prompt_update(latest_version, release_notes, installer_url, installer_name):
    """Show a Tkinter dialog asking the user if they want to update."""
    root = tk.Tk()
    root.withdraw()  # hide blank root window

    msg = (
        f"A new version of ABHA Card Studio is available!\n\n"
        f"  Current version : {CURRENT_VERSION}\n"
        f"  New version     : {latest_version}\n\n"
        f"Release notes:\n{release_notes[:300]}{'...' if len(release_notes) > 300 else ''}\n\n"
        f"Do you want to download and install the update now?"
    )

    answer = messagebox.askyesno("Update Available", msg)
    root.destroy()

    if answer:
        # Show a simple progress window
        prog_win = tk.Tk()
        prog_win.title("Downloading Update...")
        prog_win.geometry("350x80")
        prog_win.resizable(False, False)

        tk.Label(prog_win, text=f"Downloading {installer_name}...").pack(pady=(12, 4))
        progress_var = tk.IntVar()

        import tkinter.ttk as ttk
        bar = ttk.Progressbar(prog_win, variable=progress_var, maximum=100, length=300)
        bar.pack(pady=4)
        prog_win.update()

        try:
            path = download_installer(
                installer_url,
                installer_name,
                progress_callback=lambda p: (progress_var.set(p), prog_win.update())
            )
            prog_win.destroy()
            run_installer_and_exit(path)
        except Exception as e:
            prog_win.destroy()
            messagebox.showerror("Download Failed", f"Could not download update:\n{e}")


def check_for_update(silent_if_latest=True):
    """
    Main entry point. Call this at the top of your app.

    Parameters
    ----------
    silent_if_latest : bool
        If True  — shows nothing when already up to date (recommended for startup).
        If False — shows a "You are up to date" message (useful for manual check).
    """
    def _check():
        try:
            release       = get_latest_release()
            latest_ver    = release["tag_name"].lstrip("v")   # strips leading 'v' e.g. v5.3 → 5.3
            release_notes = release.get("body", "No release notes provided.")

            if version.parse(latest_ver) > version.parse(CURRENT_VERSION):
                url, name = find_installer_asset(release)
                if url:
                    prompt_update(latest_ver, release_notes, url, name)
                else:
                    if not silent_if_latest:
                        messagebox.showinfo("Update", "A new version exists but no installer was found in the release.")
            else:
                if not silent_if_latest:
                    messagebox.showinfo("Up to Date", f"You are running the latest version ({CURRENT_VERSION}).")

        except urllib.error.URLError:
            # No internet — silently skip
            pass
        except Exception as e:
            # Any other error — silently skip on startup
            print(f"[Updater] Error: {e}")

    # Run in background thread so it doesn't block app startup
    thread = threading.Thread(target=_check, daemon=True)
    thread.start()
