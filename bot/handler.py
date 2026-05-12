from servicios.telegram_service import send_message
from servicios.qvapay_service import create_invoice
from config import Config


def handle_message(chat_id: int, text: str):

    if text.lower() == "/pro":
        url = create_invoice(
            amount=10,
            description="OpenClaw PRO Plan",
            remote_id=f"{chat_id}_pro",
            webhook=Config.QVAPAY_WEBHOOK_URL
        )

        if url:
            send_message(chat_id,
                f"💎 OpenClaw PRO\n\n👉 Paga aquí:\n{url}"
            )
        else:
            send_message(chat_id, "⚠️ Error creando pago")

        return

    send_message(chat_id, f"🤖 {text}")
