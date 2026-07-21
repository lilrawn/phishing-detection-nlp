# Phishing Detector

**Created by Liron Nyambu**

An AI-powered desktop app that watches your inbox in the background and flags phishing emails in real time — with a plain-English reason for every flag and a confidence score, not just a red/green verdict. It combines a trained machine-learning model with rule-based checks (suspicious links, lookalike domains, sender verification) and works whether or not you're online.

---

## What you get in this folder

```
PhishingDetector-<your OS>/
├── PhishingDetector (installer or app)   <- run this to install
├── browser_extensions/                   <- one folder per browser
│   ├── chrome/
│   ├── brave/
│   ├── edge/
│   └── firefox/
└── README.md                             <- this file
```

## 1. Install the app

**Requirements:** Windows 10/11, macOS 11+, or a common Linux desktop (GNOME/KDE/XFCE). No Python or other setup needed — everything is bundled.

### macOS
1. Double-click `PhishingDetector.dmg`.
2. Drag **Phishing Detector** into the **Applications** folder.
3. Open it from Applications. macOS will warn that it's from an unidentified developer (it isn't signed with a paid Apple Developer certificate) — right-click the app and choose **Open**, then confirm, to get past this the first time only.

### Windows
1. Double-click `PhishingDetector-Setup.exe`.
2. Follow the installer (Next → Next → Finish). Check the box to start automatically with Windows if you want it always running.
3. Launch **Phishing Detector** from the Start Menu or desktop shortcut.

### Linux
1. Open a terminal in this folder.
2. Run: `./install.sh`
3. Launch **Phishing Detector** from your applications menu, or run `phishing-detector` in a terminal.

## 2. Connect your browser

The app watches Gmail through a small browser extension. Browsers don't allow apps to install extensions silently (that's a security feature, not a limitation of this app) — but the app automates everything up to the last click:

1. Open Phishing Detector.
2. Go to **Permissions → 🌐 Connect Your Browser...**
3. For each browser you use, click **Connect** — the app opens that browser's extensions page and copies the right folder path to your clipboard automatically.
4. Turn on **Developer Mode** if the browser shows that toggle, click **Load unpacked**, and paste the path.

Do this once per browser. After that, the extension and the dashboard find each other automatically — no codes, no accounts, nothing to reconnect.

Supported: Chrome, Brave, Edge, Firefox. (Safari isn't supported in this release — it requires a separate Apple-only build process.)

## 3. Reading the dashboard

The main window shows every email that's been scanned, most recent first:

| Column | What it means |
|---|---|
| **Type** | 🔴 PHISHING or 🟢 LEGITIMATE |
| **Source** | Where the scan came from (Gmail watcher, browser extension, etc.) |
| **From / Subject** | The email's sender and subject |
| **Confidence** | How sure the app is about its verdict, 0–100% |
| **Why Flagged** | The main reason — e.g. "Suspicious link detected," "Sender domain cannot receive mail," "Typosquatting: paypa1.com is 1 character from paypal.com" |

Double-click any row for the full detail view: every reason found, the raw ML probability vs. the combined score, and buttons to correct a mistake (mark as legitimate/phishing) — your correction helps improve future scans.

**How detection works, briefly:** every email gets a machine-learning score (trained on tens of thousands of real phishing and legitimate emails) blended with rule-based checks — known-brand impersonation, lookalike domains, urgent/pressure language, and a live check of whether the sender's domain can even receive mail. If there's no internet connection, that last check falls back to comparing against a bundled list of previously-seen phishing domains instead of failing silently.

## 4. Running in the background

By default the app runs with its dashboard open. To have it start automatically and run quietly in the background:

- **Permissions → Background Running** in the app menu, or check the box during Windows setup, or (Linux) it's enabled by the installer's `.desktop` entry.

## Troubleshooting

**Extension shows "Disconnected"** — Make sure the desktop app is running. The extension retries the connection every 10 seconds automatically once the app is back.

**macOS won't open the app ("unidentified developer")** — Right-click the app → Open → Open (this is only needed once).

**No emails showing up** — Confirm the browser extension is loaded (see step 2) and that you've granted Gmail/browser permissions from the Permissions menu.

## Uninstalling

- **macOS:** delete `Phishing Detector.app` from Applications.
- **Windows:** Settings → Apps → Phishing Detector → Uninstall.
- **Linux:** delete `~/.local/share/phishing-detector`, the shortcut in `~/.local/share/applications`, and (if enabled) the autostart entry in `~/.config/autostart`.

---

## For developers

This README is written for people installing the packaged app. If you're working on the source code, training the model, or want a full technical breakdown of the architecture — every module, how the ML pipeline works, and how to run everything from source — see [docs/TECHNICAL_GUIDE.md](docs/TECHNICAL_GUIDE.md).
