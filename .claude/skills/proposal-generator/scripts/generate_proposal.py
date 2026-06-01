#!/usr/bin/env python3
"""
Generate a ScaleShift sales proposal.

Usage (Claude passes pre-extracted JSON — preferred):
  python generate_proposal.py --json '{"clientFirstName":"Alex",...}'
  python generate_proposal.py --json '{"clientFirstName":"Alex",...}' --payment
  python generate_proposal.py --json '{"clientFirstName":"Alex",...}' --contract --payment

Usage (fallback — extracts fields from raw text):
  python generate_proposal.py --file transcript.txt
  python generate_proposal.py --text "notes..."
"""

import argparse
import json
import os
import re
import sys
import uuid
from datetime import datetime
from pathlib import Path

# Workspace root: scripts → proposal-generator → skills → .claude → workspace
ROOT = Path(__file__).parent.parent.parent.parent.parent

def _load_env():
    env_path = ROOT / ".env"
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            m = re.match(r'^([^#=\s][^=]*)=(.*)', line.strip())
            if m:
                key, val = m.group(1).strip(), m.group(2).strip()
                if key not in os.environ:
                    os.environ[key] = val

_load_env()

sys.path.insert(0, str(Path(__file__).parent))
from stripe_utils import create_deposit_payment_link

TEMPLATE_PATH = Path(__file__).parent / "templates" / "proposal.html"
TMP_DIR = ROOT / ".tmp"

MODAL_BASE_URL = os.environ.get(
    "MODAL_PROPOSAL_URL",
    "https://karlis-28774--scaleshift-proposal.modal.run",
)


def strip_contract_section(html: str) -> str:
    return re.sub(r'<!-- CONTRACT_START -->.*?<!-- CONTRACT_END -->', '', html, flags=re.DOTALL)


def fill_template(template: str, fields: dict, sign_endpoint: str, stripe_url: str, with_payment: bool = False) -> str:
    deposit = fields.get("depositCost", "")
    submit_text = f"Sign &amp; Pay {deposit} Deposit &rarr;" if with_payment else "Sign Agreement &rarr;"

    replacements = {
        "{{CLIENT_COMPANY}}":                fields.get("clientCompany", ""),
        "{{PROPOSAL_TITLE}}":                fields.get("proposalTitle", ""),
        "{{DESCRIPTION_NAME}}":              fields.get("descriptionName", ""),
        "{{CURRENT_DATE}}":                  datetime.now().strftime("%B %d, %Y"),
        "{{ONE_PARAGRAPH_PROBLEM_SUMMARY}}": fields.get("oneParagraphProblemSummary", ""),
        "{{SOLUTION_HEADING_ONE}}":          fields.get("solutionHeadingOne", ""),
        "{{SOLUTION_DESCRIPTION_ONE}}":      fields.get("solutionDescriptionOne", ""),
        "{{SOLUTION_ICON_ONE}}":             fields.get("solutionIconOne", "zap"),
        "{{SOLUTION_HEADING_TWO}}":          fields.get("solutionHeadingTwo", ""),
        "{{SOLUTION_DESCRIPTION_TWO}}":      fields.get("solutionDescriptionTwo", ""),
        "{{SOLUTION_ICON_TWO}}":             fields.get("solutionIconTwo", "settings"),
        "{{SOLUTION_HEADING_THREE}}":        fields.get("solutionHeadingThree", ""),
        "{{SOLUTION_DESCRIPTION_THREE}}":    fields.get("solutionDescriptionThree", ""),
        "{{SOLUTION_ICON_THREE}}":           fields.get("solutionIconThree", "trending-up"),
        "{{SHORT_SCOPE_DESCRIPTION_ONE}}":   fields.get("shortScopeDescriptionOne", ""),
        "{{SHORT_SCOPE_DESCRIPTION_TWO}}":   fields.get("shortScopeDescriptionTwo", ""),
        "{{SHORT_SCOPE_DESCRIPTION_THREE}}": fields.get("shortScopeDescriptionThree", ""),
        "{{MILESTONE_ONE_DAY}}":             fields.get("milestoneOneDay", ""),
        "{{MILESTONE_DESCRIPTION_ONE}}":     fields.get("milestoneDescriptionOne", ""),
        "{{MILESTONE_TWO_DAY}}":             fields.get("milestoneTwoDay", ""),
        "{{MILESTONE_DESCRIPTION_TWO}}":     fields.get("milestoneDescriptionTwo", ""),
        "{{MILESTONE_THREE_DAY}}":           fields.get("milestoneThreeDay", ""),
        "{{MILESTONE_DESCRIPTION_THREE}}":   fields.get("milestoneDescriptionThree", ""),
        "{{MILESTONE_FOUR_DAY}}":            fields.get("milestoneFourDay", ""),
        "{{MILESTONE_DESCRIPTION_FOUR}}":    fields.get("milestoneDescriptionFour", ""),
        "{{DEPOSIT_COST}}":                  deposit,
        "{{HOW_SOON}}":                      fields.get("howSoon", ""),
        "{{COST}}":                          fields.get("cost", ""),
        "{{SUBMIT_BUTTON_TEXT}}":            submit_text,
        "{{CLIENT_REGISTRATION_LINE}}":      (f"Registration No.: {fields['clientRegistrationNo']}<br>" if fields.get("clientRegistrationNo") else ""),
        "{{CLIENT_VAT_LINE}}":               (f"VAT No.: {fields['clientVatNo']}<br>" if fields.get("clientVatNo") else ""),
        "{{CLIENT_ADDRESS}}":                fields.get("clientAddress", "[Address to be confirmed]"),
        "{{CLIENT_REP_NAME}}":               fields.get("clientRepName") or f"{fields.get('clientFirstName','')} {fields.get('clientLastName','')}".strip(),
        "{{CLIENT_REP_TITLE_LINE}}":         (f", {fields['clientRepTitle']}" if fields.get("clientRepTitle") else ""),
        "{{SIGN_ENDPOINT}}":                 sign_endpoint,
        "{{STRIPE_PAYMENT_URL}}":            stripe_url if with_payment else "#",
    }
    html = template
    for key, value in replacements.items():
        html = html.replace(key, value)
    return html


def store_in_modal(proposal_uuid: str, html: str, fields: dict, stripe_url: str):
    import modal
    d = modal.Dict.from_name("scaleshift-proposals", create_if_missing=True)
    d[proposal_uuid] = {
        "html": html,
        "fields": fields,
        "stripe_url": stripe_url,
        "signed": False,
        "paid": False,
        "created_at": datetime.now().isoformat(),
    }


def extract_fields_via_cli(input_text: str) -> dict:
    """Fallback: extract fields by calling claude CLI as subprocess."""
    import subprocess, tempfile
    prompt = _build_extraction_prompt(input_text)
    claude_cmd = "claude.cmd" if sys.platform == "win32" else "claude"
    result = subprocess.run(
        [claude_cmd, "-p", "--no-session-persistence"],
        input=prompt, capture_output=True, text=True,
        encoding="utf-8", shell=False, cwd=tempfile.gettempdir(),
    )
    if result.returncode != 0:
        raise RuntimeError(f"claude CLI error: {result.stderr.strip()}")
    text = result.stdout.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return json.loads(text)


def _build_extraction_prompt(input_text: str) -> str:
    return f"""Extract proposal fields from the following sales call notes or transcript.
Return ONLY a valid JSON object — no markdown fences, no explanation.

---
{input_text}
---

Return a JSON object with exactly these keys:
{{
  "clientFirstName": "string",
  "clientLastName": "string",
  "clientCompany": "string",
  "clientEmail": "string",
  "proposalTitle": "compelling 4-8 word title for their specific proposal",
  "descriptionName": "one sentence value proposition tailored to them",
  "oneParagraphProblemSummary": "2-3 sentences describing their core problem",
  "solutionHeadingOne": "concise solution component name",
  "solutionDescriptionOne": "1-2 sentence description",
  "solutionIconOne": "single Lucide icon name e.g. zap mail bar-chart-2 users database settings trending-up cpu",
  "solutionHeadingTwo": "concise solution component name",
  "solutionDescriptionTwo": "1-2 sentence description",
  "solutionIconTwo": "single Lucide icon name",
  "solutionHeadingThree": "concise solution component name",
  "solutionDescriptionThree": "1-2 sentence description",
  "solutionIconThree": "single Lucide icon name",
  "shortScopeDescriptionOne": "what they get, specifically",
  "shortScopeDescriptionTwo": "what they get, specifically",
  "shortScopeDescriptionThree": "what they get, specifically",
  "milestoneOneDay": "e.g. Week 1 or Day 1-7",
  "milestoneDescriptionOne": "what happens at this milestone",
  "milestoneTwoDay": "e.g. Week 2",
  "milestoneDescriptionTwo": "what happens at this milestone",
  "milestoneThreeDay": "e.g. Week 3-4",
  "milestoneDescriptionThree": "what happens at this milestone",
  "milestoneFourDay": "e.g. Week 5-6 or Final",
  "milestoneDescriptionFour": "what happens at this milestone",
  "cost": "total project cost as string e.g. $3,690",
  "depositCost": "exactly 50% of cost e.g. $1,845",
  "howSoon": "client desired timeframe",
  "clientRepName": "full name of the person who will sign",
  "clientRepTitle": "their title e.g. CEO, Founder — empty string if unknown",
  "clientRegistrationNo": "company registration number if mentioned — empty string if unknown",
  "clientVatNo": "VAT number if mentioned — empty string if unknown",
  "clientAddress": "company address if mentioned — empty string if unknown"
}}"""


def _update_crm(fields: dict, proposal_url: str):
    """Update ClickUp lead: set proposal URL + status → Proposal Sent. Graceful skip if not configured."""
    leads_list = os.environ.get("CLICKUP_LEADS_LIST_ID", "")
    email      = fields.get("clientEmail", "")
    if not leads_list or not email:
        print("ClickUp not configured — skipping CRM update")
        return
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent / "lead-pipeline" / "scripts" / "lib"))
        import clickup_utils as clickup
        task = clickup.find_task_by_email(leads_list, email)
        if not task:
            print(f"No ClickUp lead found for {email} — skipping CRM update")
            return
        clickup.set_custom_fields(task["id"], leads_list, {"Proposal URL": proposal_url})
        clickup.update_task_status(task["id"], "Proposal Sent")
        print(f"ClickUp updated: {email} → Proposal Sent, URL set")
    except Exception as e:
        print(f"ClickUp CRM update failed (non-fatal): {e}")


def main():
    parser = argparse.ArgumentParser()
    input_group = parser.add_mutually_exclusive_group()
    input_group.add_argument("--json",  help="Pre-extracted fields as a JSON string (Claude provides this)")
    input_group.add_argument("--file",  help="Path to transcript file")
    input_group.add_argument("--text",  help="Transcript/notes as a string")
    parser.add_argument("--contract", action="store_true", help="Include contract section")
    parser.add_argument("--payment",  action="store_true", help="Include Stripe deposit payment button")
    args = parser.parse_args()

    # ── Get fields ────────────────────────────────
    if args.json:
        # Claude pre-extracted — fastest path
        fields = json.loads(args.json)
        company = fields.get("clientCompany", "Client")
        print(f"Fields loaded for: {company}")
    elif args.file:
        with open(args.file, "r", encoding="utf-8") as f:
            input_text = f.read()
        print("Extracting proposal fields...")
        fields = extract_fields_via_cli(input_text)
        company = fields.get("clientCompany", "Client")
        print(f"Fields extracted for: {company}")
    elif args.text:
        print("Extracting proposal fields...")
        fields = extract_fields_via_cli(args.text)
        company = fields.get("clientCompany", "Client")
        print(f"Fields extracted for: {company}")
    else:
        print("Paste your transcript/notes (Ctrl+Z + Enter on Windows to finish):")
        input_text = sys.stdin.read()
        print("Extracting proposal fields...")
        fields = extract_fields_via_cli(input_text)
        company = fields.get("clientCompany", "Client")
        print(f"Fields extracted for: {company}")

    # ── Ensure currency symbol on cost fields ─────
    for field in ("cost", "depositCost"):
        val = str(fields.get(field, "")).strip()
        if val and val[0].isdigit():
            fields[field] = f"€{val}"

    # ── Generate UUID + endpoints ─────────────────
    proposal_uuid = str(uuid.uuid4())
    sign_endpoint = f"{MODAL_BASE_URL}/p/{proposal_uuid}/sign"
    success_url   = f"{MODAL_BASE_URL}/p/{proposal_uuid}?paid=1"

    # ── Create Stripe Payment Link ────────────────
    stripe_url = "#"
    if args.payment:
        print("Creating Stripe payment link...")
        try:
            stripe_url = create_deposit_payment_link(
                company_name=company,
                deposit_amount_str=fields.get("depositCost", "$1,000"),
                proposal_uuid=proposal_uuid,
                success_url=success_url,
            )
            print(f"Stripe link created: {stripe_url}")
        except Exception as e:
            print(f"Stripe error (continuing without payment button): {e}", file=sys.stderr)

    # ── Fill template ─────────────────────────────
    print("Building proposal HTML...")
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    if not args.contract:
        template = strip_contract_section(template)
    html = fill_template(template, fields, sign_endpoint, stripe_url, with_payment=args.payment)

    # ── Save locally ──────────────────────────────
    TMP_DIR.mkdir(exist_ok=True)
    slug = company.lower().replace(" ", "_").replace("/", "_")
    local_path = TMP_DIR / f"{slug}_proposal.html"
    local_path.write_text(html, encoding="utf-8")
    print(f"Saved locally: {local_path}")

    # ── Upload to Modal ───────────────────────────
    proposal_url = f"{MODAL_BASE_URL}/p/{proposal_uuid}"
    try:
        store_in_modal(proposal_uuid, html, fields, stripe_url)
    except Exception as e:
        print(f"Modal upload failed: {e}", file=sys.stderr)
        proposal_url = f"(Modal unavailable) Local: {local_path}"

    # ── Update ClickUp CRM ────────────────────────
    _update_crm(fields, proposal_url)

    # ── Save metadata + output result ─────────────
    meta = {
        "uuid": proposal_uuid,
        "company": company,
        "fields": fields,
        "mode": {"contract": args.contract, "payment": args.payment},
        "stripe_deposit_url": stripe_url,
        "proposal_url": proposal_url,
        "local_path": str(local_path),
        "created_at": datetime.now().isoformat(),
    }
    meta_path = TMP_DIR / f"{slug}_proposal_meta.json"
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")

    print(json.dumps({"ok": True, "proposal_url": proposal_url, "local_path": str(local_path), "company": company, "cost": fields.get("cost",""), "deposit": fields.get("depositCost",""), "stripe_url": stripe_url}))


if __name__ == "__main__":
    main()
