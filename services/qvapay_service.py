import requests
import logging
from config import Config

log = logging.getLogger(__name__)

def create_invoice(amount: float, description: str, remote_id: str, webhook: str):
    try:
        resp = requests.post(
            "https://api.qvapay.com/v2/create_invoice",
            headers={
                "app-id": Config.QVAPAY_APP_ID,
                "app-secret": Config.QVAPAY_APP_SECRET,
                "Content-Type": "application/json"
            },
            json={
                "amount": amount,
                "description": description,
                "remote_id": remote_id,
                "webhook": webhook
            },
            timeout=10
        )

        resp.raise_for_status()
        data = resp.json()

        return data.get("url")

    except Exception as e:
        log.error(f"[QvaPay] Error creating invoice: {e}")
        return None
