"""
Real Gmail inbox watcher -- connects via IMAP using the app-password
credentials collected by permission_manager.request_gmail_permission() /
LoginDialog, and scans actual mail (as opposed to gmail_watcher.py's
GmailWatcher, which only ever generates simulated sample data).

On first run per account it sweeps the most recent messages in the inbox
("go through it" on startup); after that it only fetches genuinely new
mail, tracked by IMAP UID so nothing gets rescanned on every cycle.
"""
import imaplib
import email
from email.header import decode_header
import threading
import time
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent.parent))

from src.predictor import PhishingPredictor
from src.database import db

IMAP_HOST = 'imap.gmail.com'
IMAP_PORT = 993
IMAP_TIMEOUT_SECONDS = 15
INITIAL_SWEEP_COUNT = 30  # most recent messages to scan on first connection


class RealGmailWatcher(threading.Thread):
    """Background thread that scans real Gmail inboxes over IMAP."""

    def __init__(self, permission_manager, callback=None):
        super().__init__()
        self.permission_manager = permission_manager
        self.callback = callback
        self.running = False
        self.daemon = True
        self.paused = False
        ml_weight = self.permission_manager.permissions['settings'].get('ml_weight', 0.7)
        self.predictor = PhishingPredictor(ml_weight=ml_weight)

    def run(self):
        self.running = True
        print("📬 Real Gmail watcher started (IMAP)")

        while self.running:
            try:
                if not self.paused:
                    self._scan_all_accounts()
                interval = self.permission_manager.permissions['settings'].get('check_interval', 30)
                # Real IMAP is slower and rate-limited server-side -- don't
                # hammer it at the same cadence as the sample simulator.
                time.sleep(max(60, interval))
            except Exception as e:
                print(f"⚠️ Real Gmail watcher error: {e}")
                time.sleep(60)

    def stop(self):
        self.running = False
        print("🛑 Real Gmail watcher stopped")

    def _scan_all_accounts(self):
        accounts = self.permission_manager.permissions.get('gmail_accounts', [])
        for index, account in enumerate(accounts):
            if not account.get('enabled', True):
                continue
            try:
                self._scan_account(index, account)
            except Exception as e:
                print(f"⚠️ Could not scan {account.get('email', '<unknown>')}: {e}")
                print("   Check that IMAP is enabled in Gmail settings "
                      "(Settings > See all settings > Forwarding and POP/IMAP) "
                      "and that the app password is still valid.")

    def _connect(self, account):
        password = self.permission_manager.decrypt_password(account['password'])
        conn = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT, timeout=IMAP_TIMEOUT_SECONDS)
        conn.login(account['email'], password)
        conn.select('INBOX')
        return conn

    def _scan_account(self, index, account):
        conn = self._connect(account)
        try:
            status, data = conn.uid('search', None, 'ALL')
            if status != 'OK' or not data or not data[0]:
                return
            all_uids = data[0].split()

            last_uid = account.get('last_uid')
            if last_uid:
                last_uid = int(last_uid)
                uids_to_fetch = [uid for uid in all_uids if int(uid) > last_uid]
            else:
                # First time seeing this account -- sweep the most recent
                # messages rather than the entire mailbox history.
                uids_to_fetch = all_uids[-INITIAL_SWEEP_COUNT:]

            if not uids_to_fetch:
                return

            print(f"📬 Scanning {len(uids_to_fetch)} email(s) from {account['email']}...")

            newest_uid = int(all_uids[-1])
            for uid in uids_to_fetch:
                try:
                    self._fetch_and_process(conn, uid, account['email'])
                except Exception as e:
                    print(f"⚠️ Could not process message uid={uid}: {e}")

            account['last_uid'] = newest_uid
            account['last_check'] = time.strftime('%Y-%m-%d %H:%M:%S')
            self.permission_manager.save_permissions()
        finally:
            try:
                conn.close()
                conn.logout()
            except Exception:
                pass

    def _fetch_and_process(self, conn, uid, account_email):
        status, msg_data = conn.uid('fetch', uid, '(RFC822)')
        if status != 'OK' or not msg_data or msg_data[0] is None:
            return

        raw = msg_data[0][1]
        msg = email.message_from_bytes(raw)

        sender = msg.get('From', '')
        subject = self._decode_header_value(msg.get('Subject', ''))
        body, attachments = self._extract_body_and_attachments(msg)

        if not body.strip():
            return

        full_text = f"{subject}\n\n{body}"
        result = self.predictor.predict_and_save(
            full_text, sender=sender, source='gmail_real', attachments=attachments)
        if 'error' in result:
            return

        print(f"📧 [{account_email}] {result['label']}: {subject[:60]}")

        if self.callback:
            self.callback({
                'type': 'phishing_detected' if result['is_phishing'] else 'legitimate_detected',
                'email': {
                    'from': sender,
                    'subject': subject,
                    'body': body,
                },
                'result': result,
                'email_id': result.get('email_id') or f"gmail_{uid.decode() if isinstance(uid, bytes) else uid}",
                'source': 'gmail_real',
            })

    @staticmethod
    def _decode_header_value(value):
        """Decode a possibly RFC 2047 encoded-word header (e.g. subjects
        with non-ASCII characters) into a plain string."""
        if not value:
            return ''
        parts = decode_header(value)
        decoded = []
        for text, charset in parts:
            if isinstance(text, bytes):
                decoded.append(text.decode(charset or 'utf-8', errors='replace'))
            else:
                decoded.append(text)
        return ''.join(decoded)

    def _extract_body_and_attachments(self, msg):
        """Walk a parsed email.message.Message, preferring text/plain for
        the body (falling back to stripped text/html), and collecting
        attachment filenames along the way."""
        body = ''
        html_fallback = ''
        attachments = []

        if msg.is_multipart():
            for part in msg.walk():
                content_disposition = str(part.get('Content-Disposition', ''))
                filename = part.get_filename()
                if filename:
                    attachments.append(self._decode_header_value(filename))
                    continue
                if 'attachment' in content_disposition:
                    continue

                content_type = part.get_content_type()
                if content_type == 'text/plain' and not body:
                    body = self._decode_part(part)
                elif content_type == 'text/html' and not html_fallback:
                    html_fallback = self._decode_part(part)
        else:
            content_type = msg.get_content_type()
            if content_type == 'text/html':
                html_fallback = self._decode_part(msg)
            else:
                body = self._decode_part(msg)

        if not body and html_fallback:
            body = self._html_to_text_with_links(html_fallback)

        return body, attachments

    def _html_to_text_with_links(self, html):
        """Strip HTML to plain text, but preserve hrefs as a trailing
        'Links:' section first -- a plain get_text() (what
        preprocessor.clean_html does) silently drops every <a href> URL,
        which would hide the classic phishing trick of display text like
        'click here' hyperlinked to a different, malicious URL. Mirrors
        what the browser extension's content.js already does for the
        same reason."""
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, 'html.parser')
        links = [a['href'] for a in soup.find_all('a', href=True) if a['href']]
        text = soup.get_text()
        if links:
            text += '\n\nLinks:\n' + '\n'.join(f'- {url}' for url in links)
        return text

    @staticmethod
    def _decode_part(part):
        try:
            payload = part.get_payload(decode=True)
            if payload is None:
                return ''
            charset = part.get_content_charset() or 'utf-8'
            return payload.decode(charset, errors='replace')
        except Exception:
            return ''
