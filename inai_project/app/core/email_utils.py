# app/core/email_utils.py
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
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {{
                margin: 0;
                padding: 0;
                background-color: #f7f9fb;
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                color: #333;
            }}
            .container {{
                max-width: 600px;
                margin: 0 auto;
                background-color: #ffffff;
                padding: 30px;
                border-radius: 12px;
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
                text-align: center; /* Center all text */
            }}
            .brand {{
                color: #4a90e2;
                font-weight: 600;
                font-size: 28px;
            }}
            .otp {{
                font-size: 24px;
                font-weight: bold;
                color: #4a90e2;
                background-color: #eef4ff;
                padding: 10px 20px;
                display: inline-block;
                border-radius: 8px;
                margin: 20px 0;
            }}
            .footer {{
                margin-top: 30px;
                font-size: 13px;
                color: #888;
            }}
            @media only screen and (max-width: 600px) {{
                .container {{
                    padding: 20px;
                    border-radius: 0;
                    box-shadow: none;
                }}
                .otp {{
                    font-size: 20px;
                    padding: 8px 16px;
                }}
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="brand">INAI</div>
            <p>{greeting}</p>
            <p>To continue, please use the following One-Time Password (OTP):</p>
            <div class="otp">{otp}</div>
            <p>This code is valid for the next <strong>60 seconds</strong>.<br> Please do not share this OTP with anyone.</p>
            <p>If you did not request this, you can safely ignore this message.</p>
            <div class="footer">
                — Team INAI<br/>
                📩 {os.getenv("MAIL_FROM")}
            </div>
        </div>
    </body>
    </html>
    """


    message = MessageSchema(
        subject=subject,
        recipients=[email],
        body=message_body,
        subtype=MessageType.html
    )

    fm = FastMail(conf)
    await fm.send_message(message)
