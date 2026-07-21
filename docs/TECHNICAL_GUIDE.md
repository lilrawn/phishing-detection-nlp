# Phishing Detector — Technical Guide

**Project:** Phishing Detector — an AI-powered phishing email detection system, shipped both as a research/training pipeline (train and evaluate ML models on real phishing/legitimate email corpora) and as a cross-platform desktop app (real-time Gmail monitoring with browser integration).

**Created by:** Liron Nyambu

This guide is for anyone extending the code, retraining the model, or just trying to understand how it all fits together. If you only want to *install and use* the app, see the main [README.md](../README.md) instead.

---

## 1. What this project does

Phishing emails are classified using two complementary signals, blended together:

1. **A trained machine-learning model** — TF-IDF text features (2000 dimensions) plus 8 hand-engineered numeric features (URL count, urgent-keyword count, exclamation count, ALL-CAPS count, etc.), fed into a Logistic Regression classifier trained on ~56,000 real emails from the SpamAssassin corpus and the Nazario phishing corpus. On held-out test data it scores ~98% F1.
2. **Rule-based checks** — known-brand domain matching and typosquatting detection (Levenshtein distance), grammar/spelling anomalies common in phishing, urgent-language detection, and live sender-domain verification (DNS MX lookup, with an offline fallback to a curated list of domains seen in the training data's phishing samples).

The two are blended with a configurable weight (`ml_weight`, default 0.7 — i.e. 70% ML, 30% rules) into a single probability, compared against an adaptive threshold that tightens slightly as more phishing indicators stack up.

The same detection logic powers three things:
- A CLI (`run.py`) for training models and testing predictions interactively.
- A desktop app (`desktop_app/`) with a live dashboard, Gmail/browser monitoring, and system notifications.
- Browser extensions (`browser_extensions/`) that feed live Gmail content to the desktop app for scanning.

---

## 2. Architecture overview

### Training pipeline (offline, run once to produce the model)

```
data/raw/ (SpamAssassin corpus, Nazario_5.csv, email_text.csv)
        │
        ▼
src/data_collection.py (DataCollector)      -- reads and combines raw sources
        │
        ▼
data/processed/combined_dataset.csv
        │
        ▼
src/preprocessing.py (DataPreprocessor)     -- HTML stripping, tokenization,
        │                                      lemmatization, feature extraction
        ▼
src/feature_extraction.py (FeatureExtractor) -- TF-IDF vectorization
        │
        ▼
src/model_training.py (ModelTrainer)         -- trains & compares 4 models
        │                                        (Naive Bayes, Logistic Regression,
        │                                         SVM, Random Forest)
        ▼
models/*.pkl (saved model + vectorizer)
        │
        ▼
src/evaluation.py (ModelEvaluator)           -- confusion matrices, ROC curves,
                                                 comparison reports
```

`main.py`'s `train_pipeline()` runs a version of this end to end (it hand-rolls the training loop rather than calling `ModelTrainer` directly — see §4 for why that duplication was left alone).

### Live prediction (what actually runs at inference time)

```
email text + sender  ──▶  src/predictor.py (PhishingPredictor.predict())
                                │
                    ┌───────────┴────────────┐
                    ▼                        ▼
          ML score (TF-IDF +          Rule-based score
          8 numeric features          (domain/typosquat check,
          → trained model)            grammar, urgent language,
                    │                  live DNS / offline domain list)
                    └───────────┬────────────┘
                                ▼
                    blended probability, adaptive
                    threshold → is_phishing, confidence,
                    human-readable reasons
```

This is the single code path used by the CLI, the desktop app's watchers, and the browser-extension-triggered scans — there is one `PhishingPredictor` class, not one per consumer (see §5 for why that matters).

### Desktop app (live monitoring)

```
Gmail tab (via browser_extensions/<browser>/) 
        │  content.js scrapes the open email, sends it to background.js
        ▼
background.js  ──HTTP POST──▶  desktop_app/backend/browser_integration.py
                                (local server on localhost:9877)
                                        │
                                        ▼
                                PhishingPredictor.predict()
                                        │
                        ┌───────────────┼────────────────┐
                        ▼               ▼                ▼
                  HTTP response    src/database.py   GUI callback
                  (relayed back    (persists result)  (dashboard updates,
                  to the Gmail                         notification shown)
                  tab as a popup)
```

`desktop_app/backend/monitor.py`'s `EmailMonitor` is the coordinator: it owns the `GmailWatcher` (simulated inbox polling — see §7) and `BrowserWatcher`/`BrowserIntegrationServer` (the real live path), and forwards everything to the GUI via a callback.

---

## 3. Directory guide

```
phishing_detection/
├── config.py                    Central config: paths, model hyperparameters,
│                                 URGENT_KEYWORDS list used by feature extraction
├── run.py                       CLI entry point: --train / --predict / --no-rules
├── main.py                      Training pipeline (train_pipeline()) + setup_environment()
├── build.py                     Assembles the distributable zip (installer + 
│                                 browser_extensions/ + README.md)
├── requirements.txt             Core Python dependencies
│
├── src/                         Core ML + prediction library (no GUI dependencies)
│   ├── data_collection.py       DataCollector: reads SpamAssassin/Nazario/CSV sources
│   ├── preprocessing.py         TextPreprocessor (per-email cleaning), 
│   │                            DataPreprocessor (whole-dataset preprocessing)
│   ├── feature_extraction.py    FeatureExtractor: TF-IDF vectorizer + numeric scaler
│   ├── model_training.py        ModelTrainer: trains/compares the 4 candidate models
│   ├── evaluation.py            ModelEvaluator: plots and comparison reports
│   ├── database.py              EmailDatabase: SQLite store for predictions
│   │                            (training-data-oriented schema)
│   ├── predictor.py             PhishingPredictor: the single unified prediction
│   │                            engine used everywhere (see §5)
│   ├── email_verifier.py        Live MX/DNS domain verification + offline fallback
│   └── known_phishing_domains.py  Generated data file (see scripts/, below)
│
├── scripts/
│   └── extract_known_phishing_domains.py  One-off tool: regenerates
│                                            known_phishing_domains.py from the
│                                            Nazario corpus. Not run at app runtime.
│
├── desktop_app/                 The live monitoring application (has its own venv)
│   ├── main.py                  Desktop entry point: --background / --minimized / 
│   │                            --no-tray / --no-browser / --install-extension
│   ├── run_desktop.py           Thin launcher with import-error handling
│   ├── backend/
│   │   ├── monitor.py           EmailMonitor: coordinates watchers, dedupes result
│   │   │                        shapes, saves to DB, triggers callbacks
│   │   ├── gmail_watcher.py     GmailWatcher: simulated inbox polling (demo data)
│   │   ├── browser_watcher.py   BrowserWatcher: legacy raw-socket listener (9876)
│   │   ├── browser_integration.py  BrowserIntegrationServer: the real HTTP API
│   │   │                        (port 9877) the browser extensions talk to
│   │   ├── browser_detector.py  Finds installed browsers, opens their extensions
│   │   │                        page, for the "Connect Your Browser" flow
│   │   ├── permission_manager.py  Local config (~/.phishing_detector/config.json),
│   │   │                        Gmail credential encryption (Fernet), autostart
│   │   │                        setup per OS (launchd/registry/XDG)
│   │   ├── gemini_analyzer.py   Optional: Gemini API-based analysis (needs
│   │   │                        GEMINI_API_KEY env var; degrades gracefully
│   │   │                        without one)
│   │   └── browser_extension/   The extension source the backend code references
│   │                            internally (browser_extensions/ at the project
│   │                            root is the distribution copy — see §6)
│   ├── frontend/gui/
│   │   ├── main_window.py       PhishingDashboard: the main window (1,300+ lines)
│   │   ├── login_dialog.py      Gmail app-password entry
│   │   ├── settings_dialog.py   Check interval, notifications, ml_weight slider, etc.
│   │   ├── history_dialog.py    Full scan history with filtering
│   │   ├── email_detail_dialog.py  Full detail view for one scanned email
│   │   ├── notification.py      NotificationManager: OS notifications + system tray
│   │   └── browser_setup_dialog.py  "Connect Your Browser" guided-pairing dialog
│   └── installers/
│       ├── setup_macos.py       PyInstaller .app build + .dmg wrapping
│       ├── setup_windows.py     PyInstaller build + Inno Setup .iss generation
│       ├── setup_linux.py       PyInstaller onefile build + install.sh generation
│       └── requirements_desktop.txt  Desktop-only dependencies (GUI, packaging,
│                                 crypto, notifications)
│
├── browser_extensions/          Distribution copies of the extension, one per
│   ├── chrome/                  browser. chrome/brave/edge share an identical
│   ├── brave/                   Manifest V3 extension (same Chromium engine).
│   ├── edge/                    firefox/ has a Firefox-flavored manifest
│   └── firefox/                 (background.scripts instead of service_worker).
│
├── data/                        raw/ (source corpora) and processed/ (combined CSV)
├── models/                      Saved model, vectorizer, and summary stats
├── results/                     Evaluation outputs (confusion matrices, plots)
└── notebooks/                   Jupyter notebooks for exploratory analysis
```

---

## 4. The training pipeline in detail

`src/data_collection.py`'s `DataCollector` reads from three possible sources under `data/raw/`:
- `spamassassin_corpus/` — the classic SpamAssassin public corpus (spam/ham directories of raw email files).
- `email_text.csv` — a generic labeled CSV, column names auto-detected.
- `Nazario_5.csv` — a **mixed** dataset: `label=1` rows are phishing, `label=0` rows are the Enron corpus (legitimate). Any code reading this file must filter on `label`, not assume every row is phishing — see the comment in `scripts/extract_known_phishing_domains.py` for a concrete example of this being gotten wrong once and fixed.

All three get combined, deduplicated by text, shuffled, and cached to `data/processed/combined_dataset.csv`. If none of the raw sources are found, `DataCollector.create_sample_dataset()` falls back to 10 hand-written example emails — enough to exercise the pipeline, not for real training.

`src/preprocessing.py`'s `TextPreprocessor.preprocess_pipeline()` does, per email: strip HTML → replace URLs/emails with tokens → strip special characters → tokenize (NLTK, falling back to `.split()` if NLTK data is unavailable) → remove stopwords → lemmatize (WordNet). It also extracts the 8 numeric features used later: `url_count`, `email_count`, `urgent_keyword_count` (against `config.URGENT_KEYWORDS`), `text_length`, `word_count`, `avg_word_length`, `exclamation_count`, `all_caps_count`.

`src/feature_extraction.py`'s `FeatureExtractor` fits a `TfidfVectorizer` (2000 features, unigrams+bigrams, English stopwords) on the cleaned text.

`main.py`'s `train_pipeline()` combines TF-IDF (2000) + the 8 numeric features (2008 total) via `scipy.sparse.hstack`, trains 4 models (Naive Bayes gets TF-IDF only — it needs non-negative features; the other three get the combined 2008), and saves the best-performing one (by F1) as `models/best_model.pkl`.

Note: `train_pipeline()` hand-rolls this training loop rather than calling `src/model_training.py`'s `ModelTrainer` class, which does the same thing more generically. This is intentional duplication left in place during cleanup — unifying it would require a full retrain to verify the refactor didn't change results, which wasn't done in this pass. If you touch training logic, be aware there are two versions and only `main.py`'s is what actually produced the shipped model.

**Confirmed by directly inspecting the saved model:** it's a `LogisticRegression(C=10.0)` expecting exactly 2008 input features. No `feature_scaler.pkl` or `calibration_info.pkl` exists in this build — `PhishingPredictor` handles both being absent gracefully (skips scaling, uses a heuristic adaptive threshold instead of a calibrated one).

---

## 5. `PhishingPredictor` — the one prediction engine

Earlier in this project's life there were five separate predictor implementations (`predictor.py`, `predictor_simple.py`, `predictor_hybrid.py`, `predictor_enhanced.py`, `prediction_interface.py`), each written to fix or extend the previous one without deleting it. They diverged into incompatible output shapes, and one (`predictor_simple.py`) had a real bug — it never built the 8 numeric features, silently feeding the model 2000-wide input when it expected 2008. All five were consolidated into the single `src/predictor.py` you see today.

**Constructor:** `PhishingPredictor(use_rules=True, base_threshold=0.70, ml_weight=0.7)`

**`.predict(email_text, sender=None)`** returns a dict with this stable contract, used identically by the CLI, every desktop-app watcher, and every GUI dialog:

| Key | Meaning |
|---|---|
| `is_phishing` | bool |
| `label` / `classification` | Emoji + "PHISHING"/"LEGITIMATE" |
| `probability` | Blended score, 0–1 |
| `ml_probability` | Raw model output before blending, 0–1 |
| `confidence` | 0–100, distance from the decision threshold |
| `threshold` | The adaptive threshold actually used for this call |
| `reasons` | Up to 5 human-readable strings |
| `features` | The 8 numeric feature values |
| `has_links` / `suspicious_links` | URL analysis results |

**`.predict_and_save(email_text, sender=None, source='user_input')`** does the same and persists to `src/database.py`'s `db` singleton — `predict()` itself is side-effect-free.

**Rule scoring** (`_rule_score`): checks each URL against a small database of known-brand domains (`LEGITIMATE_DOMAINS`) for exact match or 1–2-character Levenshtein-distance typosquatting; checks grammar (excessive caps, multiple `!`, common misspellings); reuses the preprocessor's `urgent_keyword_count` (deliberately not a second separate keyword scan — that duplication caused a real bug once, see the comment in `predictor.py` near `_rule_score`); and calls `check_sender()` if a sender was provided.

**Sender verification** (`check_sender`): exact/typosquat match against `LEGITIMATE_DOMAINS` first, then falls through to `src/email_verifier.py`'s `check_sender_domain()` — a live MX-record DNS lookup (2-second timeout) with a fallback to `known_phishing_domains.py` (a list of domains that recurred across multiple phishing-labeled Nazario samples) when there's no network.

---

## 6. Browser extensions

`desktop_app/backend/browser_extension/` is the extension source the desktop app's own code references (e.g. for `--install-extension` instructions). `browser_extensions/` at the project root is the **distribution** copy shipped in the zip — four folders (`chrome/`, `brave/`, `edge/`, `firefox/`), built from the same `background.js`/`content.js` with per-browser manifests:

- **chrome/brave/edge**: identical Manifest V3, `background.service_worker` — all three share the Chromium extension engine.
- **firefox**: `background.scripts` instead of `service_worker` (broader Firefox-version compatibility) plus a `browser_specific_settings.gecko.id` for permanent installation without going through addons.mozilla.org.

**Flow:** `content.js` (injected into `mail.google.com`) scrapes the open email's sender/subject/body/links via DOM queries, sends it to `background.js` via `chrome.runtime.sendMessage`. `background.js` POSTs it to `http://localhost:9877/api/notification` (heartbeats every 30s, retries every 10s if disconnected). `browser_integration.py`'s HTTP server scores it synchronously and returns the result in the HTTP response body; `background.js` relays that back to the originating tab via `chrome.tabs.sendMessage`, where `content.js` renders the popup.

Safari isn't included — it requires converting the extension via Xcode into a signed macOS app, needing a paid Apple Developer account and a GUI build step that can't be automated from source.

---

## 7. Running from source

```bash
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Train (only if you don't already have models/*.pkl):
python run.py --train

# Interactive CLI prediction:
python run.py --predict
python run.py --predict --no-rules   # pure ML, no rule-based augmentation

# Desktop app:
pip install -r desktop_app/installers/requirements_desktop.txt
python desktop_app/main.py                # normal GUI
python desktop_app/main.py --background   # headless, for autostart
```

`GmailWatcher` (`desktop_app/backend/gmail_watcher.py`) doesn't connect to a real Gmail account — it randomly serves one of a handful of built-in sample emails (phishing and legitimate) on a timer, for demoing the dashboard without real credentials. The **real** live path is the browser extension → `browser_integration.py`, described in §6.

Building a distributable package: `python build.py` (auto-detects the current OS; only the macOS path is actually build-tested from this development environment — see the installer scripts' module docstrings for what's pattern-written-but-unverified on Windows/Linux).

---

## 8. Reading the GUI (for anyone extending it)

- **Stat cards** (top of the dashboard): total scanned, phishing found, legitimate, accuracy, senders tracked, extensions connected — all pulled live from `src/database.py`'s `get_statistics()` on a 5-second timer.
- **Recent Emails table**: every scan, newest first. Columns: Time, Type, Source, From, Subject, Confidence, **Why Flagged** (a one-line reason summary — double-click a row for the full list).
- **Menu → Permissions**: grant Gmail/browser access, the "Connect Your Browser" guided setup, background-running toggle.
- **Menu → View**: statistics, full history (searchable/filterable by date), sender reputation, clear log.
- **Menu → Mode**: switch between browser-extension-only, sample-emails-only, or both.
- **Settings dialog → Advanced tab**: the ML/Rules weight slider — this is a real, live-wired setting (`permission_manager.permissions['settings']['ml_weight']`), read by every `PhishingPredictor` construction site in the desktop app.

---

## Credits

Built by **Liron Nyambu**.
