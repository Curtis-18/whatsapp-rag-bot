"""
Everything that talks to Meta's Graph API: sending a reply, and verifying
that an incoming webhook really came from Meta (not someone who guessed
your webhook URL and is spamming it with fake messages).
"""
import hashlib
import hmac

import httpx

from app.config import (
    WHATSAPP_TOKEN,
    WHATSAPP_PHONE_NUMBER_ID,
    WHATSAPP_APP_SECRET,
    GRAPH_API_VERSION,
)

GRAPH_URL = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{WHATSAPP_PHONE_NUMBER_ID}/messages"


def send_text_message(to: str, body: str) -> dict:
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to,
        "type": "text",
        "text": {"body": body},
    }
    with httpx.Client(timeout=15) as http:
        r = http.post(GRAPH_URL, headers=headers, json=payload)
        r.raise_for_status()
        return r.json()


def verify_signature(payload_body: bytes, signature_header: str) -> bool:
    """
    Meta signs every webhook POST with your app secret (X-Hub-Signature-256).
    If WHATSAPP_APP_SECRET is not set we skip verification, which is fine for
    local testing but should never be the case in production.
    """
    if not WHATSAPP_APP_SECRET:
        return True
    if not signature_header:
        return False
    expected = "sha256=" + hmac.new(
        WHATSAPP_APP_SECRET.encode(), payload_body, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature_header)
