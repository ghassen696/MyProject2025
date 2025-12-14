"""from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
from typing import List
from app.config import SMTP_USERNAME, SMTP_PASSWORD, SMTP_SERVER, SMTP_PORT, SMTP_FROM

conf = ConnectionConfig(
    MAIL_USERNAME=SMTP_USERNAME,
    MAIL_PASSWORD=SMTP_PASSWORD,
    MAIL_FROM=SMTP_FROM,
    MAIL_PORT=SMTP_PORT,
    MAIL_SERVER=SMTP_SERVER,
    MAIL_TLS=True,
    MAIL_SSL=False,
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True,
)

async def send_invite_email(email: str, token: str):
    link = f"http://localhost:5173/set-password?token={token}&email={email}"  # frontend URL
    message = MessageSchema(
        subject="You're invited to join the platform",
        recipients=[email],
        body=f"Hello,\n\nClick this link to set your password and activate your account:\n{link}\n\nThanks!",
        subtype="plain"
    )
    fm = FastMail(conf)
    await fm.send_message(message)
"""
# email_utils.py
from email.message import EmailMessage
from aiosmtplib import SMTP
from app.config import SMTP_USERNAME, SMTP_PASSWORD, SMTP_SERVER, SMTP_PORT, SMTP_FROM

async def send_invite_email(email: str, token: str):
    link = f"http://193.95.30.190:5173/set-password?token={token}&email={email}"  # frontend URL
    message = EmailMessage()
    message["From"] = SMTP_FROM
    message["To"] = email
    message["Subject"] = "You're invited to join the platform"
    message.set_content(
        f"""Hello,

    Click this link to set your password and activate your account:
    {link}

    You can download the keylogger app here:
    https://drive.google.com/file/d/1dMc_J0dVEascx57ahz-7C2dOzbHbl2OY/view?usp=sharing
    Thanks!
    """
    )
    #old url https://drive.google.com/file/d/145zf9uXb6PY7CH3wfaB4RAyUSC3x5tkm/view?usp=drive_link
    #    https://drive.google.com/file/d/145zf9uXb6PY7CH3wfaB4RAyUSC3x5tkm/view?usp=sharing


    # Connect to SMTP server and send email
    smtp = SMTP(
        hostname=SMTP_SERVER,
        port=SMTP_PORT,
        start_tls=True,
        username=SMTP_USERNAME,
        password=SMTP_PASSWORD,
    )
    await smtp.connect()
    await smtp.send_message(message)
    await smtp.quit()
