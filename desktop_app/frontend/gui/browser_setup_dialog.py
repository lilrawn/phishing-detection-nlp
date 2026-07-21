"""
"Connect Your Browser" dialog -- detects installed browsers and walks the
user through loading the extension into each one. Browsers don't allow
silent extension installs, so this automates everything up to that last
click: open the extensions page, copy the folder path to the clipboard.
"""
import tkinter as tk
from tkinter import ttk, messagebox

from desktop_app.backend.browser_detector import (
    detect_installed_browsers,
    open_extensions_page,
    get_extension_folder,
)

BROWSER_DISPLAY_NAMES = {
    'chrome': 'Google Chrome',
    'brave': 'Brave',
    'edge': 'Microsoft Edge',
    'firefox': 'Firefox',
}


class BrowserSetupDialog:
    """Dialog for connecting the extension to detected browsers"""

    def __init__(self, parent):
        self.parent = parent

        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Connect Your Browser")
        self.dialog.geometry("520x420")
        self.dialog.resizable(False, False)
        self.dialog.transient(parent)
        self.dialog.grab_set()

        self.dialog.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - self.dialog.winfo_width()) // 2
        y = parent.winfo_y() + (parent.winfo_height() - self.dialog.winfo_height()) // 2
        self.dialog.geometry(f"+{x}+{y}")

        self.setup_ui()

    def setup_ui(self):
        title = ttk.Label(self.dialog, text="🌐 Connect Your Browser",
                           font=('Helvetica', 16, 'bold'))
        title.pack(pady=20)

        info_text = (
            "Load the extension once per browser to get real-time\n"
            "phishing alerts while you read Gmail. Browsers require this\n"
            "one click for security -- everything else happens automatically."
        )
        info = ttk.Label(self.dialog, text=info_text, justify=tk.CENTER)
        info.pack(pady=(0, 15))

        browsers = detect_installed_browsers()

        list_frame = ttk.Frame(self.dialog)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=20)

        if not browsers:
            ttk.Label(
                list_frame,
                text="No supported browsers were detected on this system.\n"
                     "See the README for manual installation steps.",
                justify=tk.CENTER,
                foreground='#a94442'
            ).pack(pady=30)
        else:
            for browser, path in browsers.items():
                self._add_browser_row(list_frame, browser, path)

        ttk.Button(self.dialog, text="Close", command=self.dialog.destroy,
                   width=15).pack(pady=20)

    def _add_browser_row(self, parent, browser, executable_path):
        row = ttk.Frame(parent, padding=10)
        row.pack(fill=tk.X, pady=5)

        display_name = BROWSER_DISPLAY_NAMES.get(browser, browser.title())
        ttk.Label(row, text=display_name, font=('Helvetica', 12),
                  width=18).pack(side=tk.LEFT)

        status_var = tk.StringVar(value="Not connected")
        status_label = ttk.Label(row, textvariable=status_var, foreground='#856404')
        status_label.pack(side=tk.LEFT, padx=10)

        def connect():
            folder = get_extension_folder(browser)
            if not folder.exists():
                messagebox.showerror(
                    "Extension Not Found",
                    f"Couldn't find the extension folder for {display_name}:\n{folder}"
                )
                return

            self.dialog.clipboard_clear()
            self.dialog.clipboard_append(str(folder))

            opened = open_extensions_page(browser, executable_path)

            status_var.set("Path copied ✓")
            status_label.config(foreground='#155724')

            if opened:
                messagebox.showinfo(
                    f"{display_name} Extensions Page Opened",
                    f"The folder path has been copied to your clipboard:\n\n{folder}\n\n"
                    f"1. Turn on Developer Mode (top right, if shown)\n"
                    f"2. Click 'Load unpacked'\n"
                    f"3. Paste the path and select the folder\n\n"
                    f"Once loaded, the dashboard connects automatically -- no further setup needed."
                )
            else:
                messagebox.showwarning(
                    "Couldn't Open Browser",
                    f"The path was copied to your clipboard:\n\n{folder}\n\n"
                    f"Please open {display_name} manually, go to its extensions page, "
                    f"enable Developer Mode, click 'Load unpacked', and paste the path."
                )

        ttk.Button(row, text="Connect", command=connect, width=12).pack(side=tk.RIGHT)
