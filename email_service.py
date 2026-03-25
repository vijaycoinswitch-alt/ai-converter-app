import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

load_dotenv()

# SMTP Configuration
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.titan.email")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
EMAIL_USER = os.getenv("EMAIL_USER", "support@vijaypdf.com")
EMAIL_PASS = os.getenv("EMAIL_PASS")

def send_email(to_email, subject, body, is_html=False):
    """
    Base function to send an email using SMTP.
    """
    if not EMAIL_PASS:
        print("Error: EMAIL_PASS not set in .env")
        return False

    try:
        msg = MIMEMultipart()
        msg['From'] = f"VijayPDF Support <{EMAIL_USER}>"
        msg['To'] = to_email
        msg['Subject'] = subject

        # Attach body
        part = MIMEText(body, 'html' if is_html else 'plain')
        msg.attach(part)

        # Connect and send
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_USER, EMAIL_PASS)
            server.send_message(msg)
        
        return True
    except Exception as e:
        print(f"Failed to send email: {e}")
        return False

def send_otp_email(user_email, otp):
    """
    Send a 6-digit OTP for verification.
    """
    subject = "VijayPDF OTP Verification"
    html_body = f"""
    <div style="font-family: 'Inter', sans-serif; max-width: 600px; margin: auto; padding: 20px; border: 1px solid #eee; border-radius: 10px;">
        <h2 style="color: #6366f1; text-align: center;">VijayPDF Verification</h2>
        <p>Hello,</p>
        <p>Your one-time password (OTP) for account verification is:</p>
        <div style="text-align: center; margin: 30px 0;">
            <span style="font-size: 32px; font-weight: bold; letter-spacing: 5px; color: #1e293b; background: #f1f5f9; padding: 10px 20px; border-radius: 5px;">{otp}</span>
        </div>
        <p>This code will expire in 10 minutes. If you did not request this, please ignore this email.</p>
        <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
        <p style="font-size: 12px; color: #64748b; text-align: center;">&copy; 2026 VijayPDF.com – Advanced PDF Toolkit</p>
    </div>
    """
    return send_email(user_email, subject, html_body, is_html=True)

def send_auto_reply(user_email, user_name):
    """
    Send an auto-reply after contact form submission.
    """
    subject = "Thank you for contacting VijayPDF"
    html_body = f"""
    <div style="font-family: 'Inter', sans-serif; max-width: 600px; margin: auto; padding: 20px; border: 1px solid #eee; border-radius: 10px;">
        <h2 style="color: #6366f1;">Message Received!</h2>
        <p>Hi {user_name},</p>
        <p>Thank you for contacting VijayPDF.com. Our support team has received your message and will respond shortly.</p>
        <p>In the meantime, feel free to check our <a href="https://vijaypdf.com/faq" style="color: #6366f1;">FAQ</a> for quick answers.</p>
        <br>
        <p>Best Regards,<br><strong>VijayPDF Support Team</strong></p>
        <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
        <p style="font-size: 12px; color: #64748b; text-align: center;">Support: support@vijaypdf.com</p>
    </div>
    """
    return send_email(user_email, subject, html_body, is_html=True)

def send_notification(subject, message):
    """
    Send internal notifications to support@vijaypdf.com.
    """
    # Use a specific subject prefix for internal tracking
    full_subject = f"VijayPDF Notification: {subject}"
    return send_email(EMAIL_USER, full_subject, message)

def send_password_reset_email(user_email, token):
    """
    Send a token-based password reset link.
    """
    subject = "VijayPDF Password Reset Request"
    reset_url = f"https://vijaypdf.com/reset-password/{token}" # Placeholder domain
    html_body = f"""
    <div style="font-family: 'Inter', sans-serif; max-width: 600px; margin: auto; padding: 20px; border: 1px solid #eee; border-radius: 10px;">
        <h2 style="color: #6366f1;">Password Reset</h2>
        <p>You requested a password reset for your VijayPDF account.</p>
        <p>Click the button below to set a new password:</p>
        <div style="text-align: center; margin: 30px 0;">
            <a href="{reset_url}" style="background-color: #6366f1; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; font-weight: bold;">Reset Password</a>
        </div>
        <p>If you did not request this, please ignore this email. The link will expire in 1 hour.</p>
        <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
        <p style="font-size: 12px; color: #64748b; text-align: center;">&copy; 2026 VijayPDF.com</p>
    </div>
    """
    return send_email(user_email, subject, html_body, is_html=True)

def test_connection():
    """
    Quick test for SMTP connectivity.
    """
    return send_email(EMAIL_USER, "VijayPDF SMTP Test", "SMTP integration is working correctly!")
