"""
Send emails via Gmail API using OAuth2.
Works locally (token.json) and in Modal (GMAIL_TOKEN_B64 secret).
"""

import base64
import json
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

SCOPES = ["https://mail.google.com/"]
ROOT = Path(__file__).parent.parent
FROM_EMAIL = "karlis@scaleshift.io"


def _get_credentials() -> Credentials:
    # Prefer individual env vars (scaleshift-pipeline-secrets)
    client_id     = os.environ.get("GMAIL_CLIENT_ID")
    client_secret = os.environ.get("GMAIL_CLIENT_SECRET")
    refresh_token = os.environ.get("GMAIL_REFRESH_TOKEN")

    if client_id and client_secret and refresh_token:
        creds = Credentials.from_authorized_user_info({
            "client_id":     client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
            "token_uri":     "https://oauth2.googleapis.com/token",
        }, SCOPES)
    elif os.environ.get("GMAIL_TOKEN_B64"):
        token_data = json.loads(base64.b64decode(os.environ["GMAIL_TOKEN_B64"]).decode())
        creds = Credentials.from_authorized_user_info(token_data, SCOPES)
    else:
        token_file = ROOT / "token.json"
        if not token_file.exists():
            raise FileNotFoundError("token.json not found. Run: python execution/setup_gmail.py")
        creds = Credentials.from_authorized_user_file(str(token_file), SCOPES)

    if creds.expired and creds.refresh_token:
        creds.refresh(Request())

    return creds


def send_html_email(to: str, subject: str, html_body: str, cc: str = None):
    """Send an HTML email from karlis@scaleshift.io."""
    creds = _get_credentials()
    service = build("gmail", "v1", credentials=creds)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = FROM_EMAIL
    msg["To"] = to
    if cc:
        msg["Cc"] = cc

    msg.attach(MIMEText(html_body, "html", "utf-8"))

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    service.users().messages().send(userId="me", body={"raw": raw}).execute()


def build_signed_email(fields: dict, signature_data_url: str, signed_at: str, client_ip: str) -> str:
    """Build the HTML email body sent after a proposal is signed."""
    company     = fields.get("clientCompany", "")
    cost        = fields.get("cost", "")
    deposit     = fields.get("depositCost", "")
    how_soon    = fields.get("howSoon", "")
    rep_name    = fields.get("clientRepName", "") or f"{fields.get('clientFirstName','')} {fields.get('clientLastName','')}".strip()
    s1_title    = fields.get("solutionHeadingOne", "")
    s2_title    = fields.get("solutionHeadingTwo", "")
    s3_title    = fields.get("solutionHeadingThree", "")
    scope1      = fields.get("shortScopeDescriptionOne", "")
    scope2      = fields.get("shortScopeDescriptionTwo", "")
    scope3      = fields.get("shortScopeDescriptionThree", "")
    reg_no      = fields.get("clientRegistrationNo", "")
    vat_no      = fields.get("clientVatNo", "")
    address     = fields.get("clientAddress", "")
    rep_title   = fields.get("clientRepTitle", "")

    reg_line    = f"<br>Registration No.: {reg_no}" if reg_no else ""
    vat_line    = f"<br>VAT No.: {vat_no}" if vat_no else ""
    addr_line   = f"<br>{address}" if address else ""
    title_line  = f", {rep_title}" if rep_title else ""

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
  body {{ font-family: Arial, sans-serif; background:#f7f6f2; margin:0; padding:20px; color:#0f0e14; }}
  .wrap {{ max-width:600px; margin:0 auto; background:#fff; border-radius:12px; overflow:hidden; box-shadow:0 4px 24px rgba(0,0,0,0.08); }}
  .hdr {{ background:#0b0b0f; padding:28px 36px; display:flex; align-items:center; gap:10px; }}
  .hdr img {{ width:30px; height:30px; border-radius:50%; }}
  .hdr span {{ color:#f0eff4; font-weight:700; font-size:1rem; }}
  .body {{ padding:36px; }}
  h1 {{ font-size:1.4rem; font-weight:700; margin:0 0 6px; }}
  .sub {{ color:#4a4860; font-size:0.9rem; margin-bottom:1.5rem; }}
  .row {{ display:flex; justify-content:space-between; padding:9px 0; border-bottom:1px solid #f0eff4; font-size:0.85rem; }}
  .lbl {{ color:#9896aa; font-weight:600; }}
  .val {{ color:#0f0e14; }}
  .sig-box {{ margin:1.5rem 0; padding:1.25rem; background:#f7f6f2; border-radius:8px; }}
  .sig-box h3 {{ font-size:0.65rem; font-weight:700; letter-spacing:0.14em; text-transform:uppercase; color:#F2721C; margin:0 0 10px; }}
  .sig-box img {{ max-width:280px; background:#fff; border:1px solid #e8e6e0; border-radius:6px; padding:8px; display:block; }}
  .audit {{ font-size:0.75rem; color:#9896aa; margin-top:8px; }}
  .contract {{ margin-top:2rem; padding-top:2rem; border-top:2px solid #f0eff4; }}
  .contract h2 {{ font-size:0.95rem; font-weight:700; margin-bottom:1rem; }}
  .ct {{ font-size:0.8rem; color:#4a4860; line-height:1.7; }}
  .ct h4 {{ font-size:0.8rem; font-weight:700; color:#0f0e14; margin:1rem 0 4px; }}
  .ct ul {{ padding-left:1.1rem; margin:4px 0; }}
  .ct li {{ margin-bottom:3px; }}
  .parties {{ display:flex; gap:1rem; margin:1rem 0; }}
  .party {{ flex:1; background:#f7f6f2; border-radius:6px; padding:12px; font-size:0.78rem; line-height:1.6; }}
  .pty-lbl {{ font-size:0.6rem; font-weight:700; letter-spacing:0.12em; text-transform:uppercase; color:#F2721C; margin-bottom:4px; }}
  .ftr {{ background:#0b0b0f; padding:20px 36px; color:#5e5c72; font-size:0.75rem; text-align:center; }}
  .ftr a {{ color:#F2721C; text-decoration:none; }}
</style>
</head>
<body>
<div class="wrap">
  <div class="hdr">
    <img src="https://scaleshift.io/sula_agency.png" alt="Scaleshift">
    <span>Scaleshift</span>
  </div>
  <div class="body">
    <h1>Proposal signed ✓</h1>
    <p class="sub">Here's your copy of the signed agreement. Keep this for your records.</p>

    <div class="row"><span class="lbl">Client</span><span class="val">{company}</span></div>
    <div class="row"><span class="lbl">Signed by</span><span class="val">{rep_name}{title_line}</span></div>
    <div class="row"><span class="lbl">Date signed</span><span class="val">{signed_at}</span></div>
    <div class="row"><span class="lbl">Total project fee</span><span class="val">{cost}</span></div>
    <div class="row"><span class="lbl">Deposit due today</span><span class="val">{deposit}</span></div>
    <div class="row"><span class="lbl">IP address</span><span class="val">{client_ip}</span></div>

    <div class="sig-box">
      <h3>Client Signature</h3>
      <img src="{signature_data_url}" alt="Signature">
      <p class="audit">Signed {signed_at} · IP {client_ip}</p>
    </div>

    <div class="contract">
      <h2>Technical Services Agreement</h2>
      <div class="ct">
        <p>This Agreement is made as of <strong>{signed_at}</strong>, by and between:</p>
        <div class="parties">
          <div class="party">
            <div class="pty-lbl">The Consultant</div>
            <strong>Kārlis Leilands</strong><br>
            Personal Code: 300801-20704<br>
            Krišjāņa Barona iela 24/26-26, LV-1050, Riga, Latvia<br>
            Non-VAT Payer (Latvia)<br>
            karlis@scaleshift.io
          </div>
          <div class="party">
            <div class="pty-lbl">The Client</div>
            <strong>{company}</strong>{reg_line}{vat_line}{addr_line}<br>
            Represented by: {rep_name}{title_line}
          </div>
        </div>

        <h4>1. Scope of Work</h4>
        <ul>
          <li><strong>{s1_title}</strong> — {scope1}</li>
          <li><strong>{s2_title}</strong> — {scope2}</li>
          <li><strong>{s3_title}</strong> — {scope3}</li>
        </ul>
        <p>Timeline: Delivery within <strong>{how_soon}</strong> from payment commencement.<br>
        Documentation: Text &amp; video walkthroughs included.</p>

        <h4>2. Payment Terms</h4>
        <ul>
          <li>Total fee: <strong>{cost}</strong></li>
          <li>50% upfront ({deposit}), 50% upon delivery ({deposit})</li>
          <li>Payment via Stripe invoice. No VAT charged (non-VAT payer, Latvia).</li>
        </ul>

        <h4>3. Intellectual Property</h4>
        <p>Upon full payment, all IP rights to assets developed specifically for the Client transfer to the Client.</p>

        <h4>4. Confidentiality</h4>
        <p>The Consultant will maintain confidentiality of all Client data, credentials, and business logic shared during the project.</p>

        <h4>5. Liability &amp; Third-Party Services</h4>
        <ul>
          <li>The Consultant is not responsible for interruptions or changes by third-party providers (OpenAI, n8n, etc.).</li>
          <li>The Client indemnifies the Consultant against legal claims from use of generated content or automated systems.</li>
        </ul>

        <h4>6. Governing Law</h4>
        <p>Governed by the laws of the Republic of Latvia. Disputes resolved through negotiation or Latvian courts.</p>

        <h4>Signatures</h4>
        <p><strong>Consultant:</strong> Kārlis Leilands (karlis@scaleshift.io)<br>
        <strong>Client:</strong> {rep_name}{title_line} — <em>digitally signed above</em></p>
      </div>
    </div>
  </div>
  <div class="ftr">
    Questions? <a href="mailto:karlis@scaleshift.io">karlis@scaleshift.io</a> &nbsp;·&nbsp; scaleshift.io
  </div>
</div>
</body>
</html>"""
