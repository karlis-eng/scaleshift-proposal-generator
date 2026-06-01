"""
Stripe utilities for proposal payment links.
Creates Payment Links (non-expiring) for deposit and completion payments.
"""

import os
import re
from pathlib import Path
import urllib3
import stripe

# Fix Windows SSL cert verification — Stripe passes verify= per-request, must set on HTTP client
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
stripe.default_http_client = stripe.RequestsClient(verify_ssl_certs=False)

# Workspace root = scripts → proposal-generator → skills → .claude → workspace
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
stripe.api_key = os.environ["STRIPE_SECRET_KEY"]


def _parse_amount_cents(amount_str: str) -> int:
    """Parse a cost string like '$1,845' or '1845.00' into cents."""
    cleaned = re.sub(r"[^0-9.]", "", amount_str)
    return int(float(cleaned) * 100)


def create_deposit_payment_link(company_name: str, deposit_amount_str: str, proposal_uuid: str, success_url: str) -> str:
    """Create a Stripe Payment Link for the 50% deposit. Returns the payment link URL."""
    amount_cents = _parse_amount_cents(deposit_amount_str)

    product = stripe.Product.create(
        name=f"ScaleShift — {company_name} · Project Deposit",
        metadata={"proposal_uuid": proposal_uuid, "type": "deposit"},
    )

    price = stripe.Price.create(
        product=product.id,
        unit_amount=amount_cents,
        currency="eur",
    )

    payment_link = stripe.PaymentLink.create(
        line_items=[{"price": price.id, "quantity": 1}],
        after_completion={"type": "redirect", "redirect": {"url": success_url}},
        metadata={"proposal_uuid": proposal_uuid, "type": "deposit"},
    )

    return payment_link.url


def create_completion_payment_link(company_name: str, completion_amount_str: str, proposal_uuid: str) -> str:
    """Create a Stripe Payment Link for the final 50% completion payment."""
    amount_cents = _parse_amount_cents(completion_amount_str)

    product = stripe.Product.create(
        name=f"ScaleShift — {company_name} · Project Completion",
        metadata={"proposal_uuid": proposal_uuid, "type": "completion"},
    )

    price = stripe.Price.create(
        product=product.id,
        unit_amount=amount_cents,
        currency="eur",
    )

    payment_link = stripe.PaymentLink.create(
        line_items=[{"price": price.id, "quantity": 1}],
        metadata={"proposal_uuid": proposal_uuid, "type": "completion"},
    )

    return payment_link.url
