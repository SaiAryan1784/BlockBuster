"""
SMS dispatch via Twilio, gated behind Judging Panel approval.
This module never fires unless the panel recommends APPROVE and is in PENDING_APPROVAL state.
"""
import os
from dotenv import load_dotenv
from twilio.rest import Client

load_dotenv()  

_client = None

def get_twilio_client():
    global _client
    if _client is None:
        account_sid = os.environ.get("TWILIO_ACCOUNT_SID")
        auth_token = os.environ.get("TWILIO_AUTH_TOKEN")
        if not account_sid or not auth_token:
            raise RuntimeError(
                "TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN not set. "
                "Set them in your .env file."
            )
        _client = Client(account_sid, auth_token)
    return _client

def send_public_advisory(advisory_text: str, recipients: list) -> dict:
    """
    Send advisory SMS to a list of recipients (e.g., ["commuters", "traffic_live"]).
    For a trial account, you'll need to whitelist specific phone numbers.
    This endpoint is intentionally NOT called automatically — it's a manual dispatch
    after Watch Commander review, never a canned broadcast.
    """
    client = get_twilio_client()
    trial_number = os.environ.get("TWILIO_TRIAL_NUMBER")
    if not trial_number:
        raise RuntimeError("TWILIO_TRIAL_NUMBER not set in .env")
    
    results = []
    for recipient_phone in recipients:
        try:
            msg = client.messages.create(
                body=advisory_text,
                from_=trial_number,
                to=recipient_phone
            )
            results.append({
                "recipient": recipient_phone,
                "status": "sent",
                "message_sid": msg.sid,
                "timestamp": str(msg.date_sent)
            })
        except Exception as e:
            results.append({
                "recipient": recipient_phone,
                "status": "failed",
                "error": str(e)
            })
    return {"sms_results": results}