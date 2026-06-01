"""
Modal web app — serves interactive proposal pages with signature capture.
Deploy: python -m modal deploy execution/serve_proposal.py
"""

import modal

app = modal.App("scaleshift-proposal")

image = (
    modal.Image.debian_slim()
    .pip_install("fastapi", "pydantic", "google-auth", "google-auth-oauthlib", "google-api-python-client")
    .add_local_file("execution/gmail_utils.py", "/root/gmail_utils.py")
)

# Persistent dict — stores all proposals by UUID
proposals = modal.Dict.from_name("scaleshift-proposals", create_if_missing=True)

gmail_secret = modal.Secret.from_name("gmail-token")


@app.function(image=image, secrets=[gmail_secret])
@modal.asgi_app(label="scaleshift-proposal")
def fastapi_app():
    from datetime import datetime, timezone

    from fastapi import FastAPI, HTTPException, Request
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import HTMLResponse, JSONResponse
    from pydantic import BaseModel

    web_app = FastAPI()
    web_app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )

    class SignaturePayload(BaseModel):
        signature: str  # base64 PNG data URL

    @web_app.get("/p/{uuid}", response_class=HTMLResponse)
    async def get_proposal(uuid: str):
        try:
            data = proposals[uuid]
        except KeyError:
            raise HTTPException(status_code=404, detail="Proposal not found.")
        return HTMLResponse(content=data["html"])

    @web_app.post("/p/{uuid}/sign")
    async def sign_proposal(uuid: str, payload: SignaturePayload, request: Request):
        try:
            data = proposals[uuid]
        except KeyError:
            raise HTTPException(status_code=404, detail="Proposal not found.")

        # Capture audit trail
        client_ip  = request.headers.get("x-forwarded-for", request.client.host if request.client else "unknown")
        signed_at  = datetime.now(timezone.utc).strftime("%B %d, %Y at %H:%M UTC")

        data["signature"]  = payload.signature
        data["signed"]     = True
        data["signed_at"]  = signed_at
        data["client_ip"]  = client_ip
        proposals[uuid] = data

        # Send email in background (don't block the response)
        _send_signed_email(data, payload.signature, signed_at, client_ip)

        # Notify lead pipeline (updates Monday.com status → "Signed")
        fields = data.get("fields", {})
        _notify_pipeline("proposal-signed", {
            "email":         fields.get("clientEmail", ""),
            "company":       fields.get("clientCompany", ""),
            "proposal_uuid": uuid,
            "signed_at":     signed_at,
        })

        return JSONResponse({"status": "ok"})

    @web_app.post("/stripe-webhook")
    async def stripe_webhook(request: Request):
        """
        Stripe sends payment_intent.succeeded here when a deposit is paid.
        Verifies the webhook signature then notifies the lead pipeline.
        Register this URL in Stripe Dashboard → Webhooks.
        """
        import os, hashlib, hmac, time
        payload = await request.body()
        sig_header = request.headers.get("stripe-signature", "")
        secret = os.environ.get("STRIPE_WEBHOOK_SECRET", "")

        if secret:
            # Verify Stripe signature
            try:
                parts = dict(p.split("=", 1) for p in sig_header.split(","))
                ts = int(parts.get("t", 0))
                expected = hmac.new(
                    secret.encode(), f"{ts}.{payload.decode()}".encode(), hashlib.sha256
                ).hexdigest()
                if not hmac.compare_digest(expected, parts.get("v1", "")):
                    from fastapi import HTTPException
                    raise HTTPException(status_code=400, detail="Invalid Stripe signature")
            except Exception as e:
                print(f"Stripe signature error: {e}")
                from fastapi import HTTPException
                raise HTTPException(status_code=400, detail="Signature verification failed")

        import json
        event = json.loads(payload)
        if event.get("type") == "payment_intent.succeeded":
            pi = event["data"]["object"]
            metadata = pi.get("metadata", {})
            if metadata.get("type") == "deposit":
                proposal_uuid = metadata.get("proposal_uuid", "")
                # Look up the proposal to get the client email
                email = ""
                company = ""
                try:
                    data = proposals[proposal_uuid]
                    fields = data.get("fields", {})
                    email = fields.get("clientEmail", "")
                    company = fields.get("clientCompany", "")
                except Exception:
                    pass
                _notify_pipeline("deposit-paid", {
                    "email": email,
                    "company": company,
                    "proposal_uuid": proposal_uuid,
                })
                print(f"Deposit paid: {company} ({email})")

        return {"received": True}

    @web_app.get("/health")
    async def health():
        return {"status": "ok", "proposals": len(list(proposals.keys()))}

    return web_app


def _notify_pipeline(event: str, payload: dict):
    """POST to the lead-pipeline Modal app to update CRM. Fire-and-forget."""
    import os, json, urllib.request
    base_url = os.environ.get("PIPELINE_BASE_URL", "")
    if not base_url:
        print(f"PIPELINE_BASE_URL not set — skipping pipeline notification for {event}")
        return
    try:
        url = f"{base_url}/pipeline/{event}"
        body = json.dumps(payload).encode()
        req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=10) as resp:
            print(f"Pipeline notified: {event} → {resp.status}")
    except Exception as e:
        print(f"Pipeline notification failed (non-fatal): {e}")


def _send_signed_email(data: dict, signature_data_url: str, signed_at: str, client_ip: str):
    """Send the signed agreement email to client + Karlis."""
    import os
    import sys

    # Only attempt if Gmail secret is configured
    if not os.environ.get("GMAIL_TOKEN_B64"):
        print("Gmail secret not set — skipping email.")
        return

    try:
        sys.path.insert(0, "/root")
        from gmail_utils import build_signed_email, send_html_email

        fields       = data.get("fields", {})
        client_email = fields.get("clientEmail", "")
        company      = fields.get("clientCompany", "Client")

        if not client_email:
            print(f"No client email for {company} — skipping.")
            return

        subject  = f"Your signed proposal — {company} × Scaleshift"
        html     = build_signed_email(fields, signature_data_url, signed_at, client_ip)

        # Email client and CC Karlis
        send_html_email(to=client_email, subject=subject, cc="karlis@scaleshift.io", html_body=html)
        print(f"✅ Signed agreement emailed to {client_email}")

    except Exception as e:
        # Never crash the sign endpoint over email failure
        print(f"Email send error: {e}")
