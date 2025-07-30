# app/utils/email_utils.py
import os
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType
from pydantic import EmailStr
from dotenv import load_dotenv

load_dotenv()

conf = ConnectionConfig(
    MAIL_USERNAME=os.getenv("MAIL_USERNAME"),
    MAIL_PASSWORD=os.getenv("MAIL_PASSWORD"),
    MAIL_FROM=os.getenv("MAIL_FROM"),
    MAIL_PORT=int(os.getenv("MAIL_PORT", 587)),
    MAIL_SERVER=os.getenv("MAIL_SERVER"),
    MAIL_FROM_NAME=os.getenv("MAIL_FROM_NAME", "INAI"),
    MAIL_STARTTLS=os.getenv("MAIL_STARTTLS", "True").lower() == "true",
    MAIL_SSL_TLS=os.getenv("MAIL_SSL_TLS", "False").lower() == "true",
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True
)

async def send_email_otp(email: EmailStr, otp: str, purpose: str = "signup"):
    if purpose == "signup":
        subject = "🔐 INAI Email Verification Code"
        greeting = "Thank you for registering with INAI!"
    elif purpose == "email_change":
        subject = "✉️ INAI Email Change Verification Code"
        greeting = "You requested to change your email address on INAI."
    elif purpose == "password_reset":
        subject = "🔑 INAI Password Reset OTP"
        greeting = "You requested to reset your password for INAI."
    else:
        subject = "🔐 INAI Verification Code"
        greeting = "Here is your verification code."

    message_body = f"""
Hi there 👋,

{greeting}

To continue, please use the following One-Time Password (OTP):

🔐 Your OTP is: {otp}

This code is valid for the next 10 minutes. Please do not share this OTP with anyone.

If you did not request this, you can ignore this message.

Best regards,  
Team INAI  
📩 {os.getenv("MAIL_FROM")}
"""

    message = MessageSchema(
        subject=subject,
        recipients=[email],
        body=message_body,
        subtype=MessageType.plain
    )

    fm = FastMail(conf)
    await fm.send_message(message)
