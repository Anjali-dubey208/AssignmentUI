"""
Sends campaign emails over SMTP. If SMTP credentials aren't configured,
runs in "simulate" mode so the Send -> Report flow can still be demoed
end-to-end without real credentials.
"""
import smtplib
import ssl
import random
from email.message import EmailMessage

from config import Config


def send_campaign(recipients, subject, body, attachment=None):
    """
    recipients: list of email strings
    attachment: optional dict {"filename": str, "data": bytes, "mimetype": str}
    Returns dict: {"delivered": [...], "failed": [...]}
    """
    delivered, failed = [], []

    simulate = not (Config.SMTP_USER and Config.SMTP_PASSWORD)

    if simulate:
        for r in recipients:
            # Simulate a realistic ~95% delivery rate for demo purposes
            (delivered if random.random() > 0.05 else failed).append(r)
        return {"delivered": delivered, "failed": failed, "simulated": True}

    context = ssl.create_default_context()
    try:
        with smtplib.SMTP(Config.SMTP_HOST, Config.SMTP_PORT) as server:
            server.starttls(context=context)
            server.login(Config.SMTP_USER, Config.SMTP_PASSWORD)

            for r in recipients:
                try:
                    msg = EmailMessage()
                    msg["Subject"] = subject
                    msg["From"] = f"{Config.SENDER_NAME} <{Config.SMTP_USER}>"
                    msg["To"] = r
                    msg.set_content(body)

                    if attachment:
                        maintype, _, subtype = attachment["mimetype"].partition("/")
                        msg.add_attachment(
                            attachment["data"],
                            maintype=maintype or "application",
                            subtype=subtype or "octet-stream",
                            filename=attachment["filename"],
                        )

                    server.send_message(msg)
                    delivered.append(r)
                except Exception:
                    failed.append(r)
    except Exception:
        # Couldn't even connect/login -> everything failed
        failed = list(recipients)
        delivered = []

    return {"delivered": delivered, "failed": failed, "simulated": False}
