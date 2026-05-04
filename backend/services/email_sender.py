import os
import re
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from urllib.parse import quote
import asyncio
from db import companies_collection
from bson import ObjectId

# Auto-detect SMTP settings by email domain — no user config needed
SMTP_PROVIDERS = {
    "gmail.com":       {"host": "smtp.gmail.com",       "port": 587},
    "googlemail.com":  {"host": "smtp.gmail.com",       "port": 587},
    "outlook.com":     {"host": "smtp.office365.com",   "port": 587},
    "hotmail.com":     {"host": "smtp.office365.com",   "port": 587},
    "live.com":        {"host": "smtp.office365.com",   "port": 587},
    "msn.com":         {"host": "smtp.office365.com",   "port": 587},
    "yahoo.com":       {"host": "smtp.mail.yahoo.com",  "port": 465},
    "yahoo.co.uk":     {"host": "smtp.mail.yahoo.com",  "port": 465},
    "yahoo.co.in":     {"host": "smtp.mail.yahoo.com",  "port": 465},
    "icloud.com":      {"host": "smtp.mail.me.com",     "port": 587},
    "me.com":          {"host": "smtp.mail.me.com",     "port": 587},
    "zoho.com":        {"host": "smtp.zoho.com",        "port": 587},
}

DEFAULT_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
DEFAULT_PORT = int(os.getenv("SMTP_PORT", 587))


def _resolve_smtp(email: str) -> tuple[str, int]:
    """Derive SMTP host and port from the user's email domain."""
    domain = email.split("@")[-1].lower() if "@" in email else ""
    provider = SMTP_PROVIDERS.get(domain)
    if provider:
        return provider["host"], provider["port"]
    return DEFAULT_HOST, DEFAULT_PORT


def _inject_tracking(html_content: str, tracking_token: str, base_url: str) -> str:
    """
    Two-step tracking injection:

    1. Rewrite all href="http(s)://..." links so they pass through the
       click-tracking endpoint and then redirect to the original URL.

    2. Append a 1×1 transparent pixel <img> at the end of the HTML.
       Appending (rather than injecting before </body>) is safe for all
       email templates regardless of whether they include a </body> tag.
    """
    # ── Step 1: Rewrite links ─────────────────────────────────────────────────
    def rewrite_link(match: re.Match) -> str:
        original_url = match.group(1)
        encoded_url  = quote(original_url, safe="")
        track_url    = (
            f"{base_url}/api/track/click"
            f"?token={tracking_token}&url={encoded_url}"
        )
        return f'href="{track_url}"'

    html_content = re.sub(r'href="(https?://[^"]+)"', rewrite_link, html_content)

    # ── Step 1.5: Convert bare URLs to clickable tracked links ───────────────
    # This regex matches URLs that are NOT preceded by href=" or similar attributes,
    # and NOT already inside an <a> tag content.
    # We use a trick: match <a> tags first and keep them, or match URLs.
    def rewrite_bare_link(match: re.Match) -> str:
        tag_match = match.group(1)
        url_match = match.group(2)
        
        if tag_match:
            return tag_match # Return <a> tag as-is
            
        # Avoid double-rewriting if it's already a tracking URL
        if base_url in url_match:
            return url_match
        
        encoded_url  = quote(url_match, safe="")
        track_url    = (
            f"{base_url}/api/track/click"
            f"?token={tracking_token}&url={encoded_url}"
        )
        return f'<a href="{track_url}">{url_match}</a>'
        
    # Pattern: match <a>...</a> OR a standalone URL
    pattern = r'(<a\s+[^>]*>.*?</a>)|(?<!["\'])(https?://[^\s<>"\']+)'
    html_content = re.sub(pattern, rewrite_bare_link, html_content, flags=re.IGNORECASE | re.DOTALL)

    # ── Step 2: Inject open-tracking pixel ────────────────────────────────────
    pixel_endpoint = f"{base_url}/api/track/open?token={tracking_token}"
    pixel = (
        f'<img src="{pixel_endpoint}&ngrok-skip-browser-warning=1" '
        f'width="1" height="1" '
        f'style="display:none!important;mso-hide:all;border:0;margin:0;padding:0" '
        f'alt="" />'
    )
    
    # Avoid double-injecting the SAME PIXEL
    if pixel_endpoint in html_content:
        return html_content

    if "</body>" in html_content.lower():
        # Inject just before the closing body tag to improve reliability/deliverability
        return re.sub(r'(</body>)', f'{pixel}\\1', html_content, flags=re.IGNORECASE)
    
    return html_content + pixel


class EmailService:
    @staticmethod
    async def send_email(
        company_id: str,
        to_address: str,
        subject: str,
        html_content: str,
        tracking_token: str | None = None,
    ):
        # TEMPORARY OVERRIDE: Default receiver for testing
        to_address = "mishraabhishek1703@gmail.com"

        # 1. Get SMTP credentials from company profile
        company = await companies_collection.find_one({"_id": ObjectId(company_id)})
        if not company:
            raise ValueError("Company not found")

        settings  = company.get("settings", {})
        smtp_user = settings.get("smtp_user") or os.getenv("SMTP_USER")
        smtp_pass = settings.get("smtp_pass") or os.getenv("SMTP_PASS")

        # 2. Auto-detect host and port from email domain (no user input needed)
        smtp_host, smtp_port = _resolve_smtp(smtp_user or "")
        # Allow .env override for custom/self-hosted SMTP servers
        if os.getenv("SMTP_HOST"):
            smtp_host = os.getenv("SMTP_HOST")
        if os.getenv("SMTP_PORT"):
            smtp_port = int(os.getenv("SMTP_PORT"))

        default_company_email = company.get("email", "noreply@strategicgrid.ai")
        from_email = settings.get("from_email", smtp_user or default_company_email)
        from_name  = settings.get("from_name", company.get("company_name", "Sales Agent"))

        # 3. Inject tracking pixel + rewrite links (if a token was provided)
        if tracking_token:
            base_url     = os.getenv("BACKEND_BASE_URL", "http://localhost:8000")
            html_content = _inject_tracking(html_content, tracking_token, base_url)

        if not to_address or "@" not in str(to_address):
            print(f"Skipping email send: Invalid or missing recipient address '{to_address}'")
            raise ValueError(f"Invalid recipient email address: {to_address}")

        if not smtp_user or not smtp_pass:
            # Fallback for local testing if SMTP isn't configured
            print(f"\n[MOCK EMAIL] To: {to_address} | Subject: {subject}")
            print(f"Content snippet: {html_content[:120]}...\n")
            await asyncio.sleep(1)
            return True

        # 4. Construct message
        msg             = MIMEMultipart("alternative")
        msg["Subject"]  = subject
        msg["From"]     = f"{from_name} <{from_email}>"
        msg["To"]       = to_address

        part = MIMEText(html_content, "html")
        msg.attach(part)

        # 5. Send via SMTP (port 465 = SSL, everything else = STARTTLS)
        def _send():
            if smtp_port == 465:
                server = smtplib.SMTP_SSL(smtp_host, smtp_port)
            else:
                server = smtplib.SMTP(smtp_host, smtp_port)
                server.ehlo()
                server.starttls()
                server.ehlo()
            server.login(smtp_user, smtp_pass)
            server.sendmail(from_email, to_address, msg.as_string())
            server.quit()

        try:
            await asyncio.to_thread(_send)
            return html_content # Return the tracked HTML so it can be saved to DB
        except Exception as e:
            print(f"Failed to send email via SMTP: {e}")
            raise ValueError(f"SMTP Error: {str(e)}") from e
