#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Email Sender Module
- Sends HTML emails with embedded inline images (CID)
- Uses smtplib and standard library (no pip dependencies required)
- Loads SMTP configurations from environment variables or falls back to SMTP settings
"""

import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from pathlib import Path

# === SMTP Configurations ===
# Set these environment variables or fill them in below for production
SMTP_SERVER = os.environ.get("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))  # 587 for TLS, 465 for SSL
SMTP_USER = os.environ.get("SMTP_USER", "hsu.yungfeng63@gmail.com")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "htjvszgyhsghaqma")

DEFAULT_SENDER = SMTP_USER or "noreply@doctor-toolbox.com"

def send_marketing_email(recipient_email, subject, html_content, image_path=None, sender=DEFAULT_SENDER):
    """
    Sends an HTML email to recipient_email, with optional inline image attachment (CID: poster_img).
    """
    if not SMTP_USER or not SMTP_PASSWORD:
        print("  ⚠️ SMTP credentials not set! Skipping email send. (Set SMTP_USER and SMTP_PASSWORD)")
        return False, "smtp_credentials_missing"

    print(f"  ✉️ Preparing email to {recipient_email} via {SMTP_SERVER}...")
    
    # Create email container
    msg = MIMEMultipart('related')
    msg['Subject'] = subject
    msg['From'] = sender
    msg['To'] = recipient_email

    # Alternative part for text/html
    msg_alternative = MIMEMultipart('alternative')
    msg.attach(msg_alternative)

    # Attach HTML content
    msg_html = MIMEText(html_content, 'html', 'utf-8')
    msg_alternative.attach(msg_html)

    # Attach inline image if provided
    if image_path and Path(image_path).exists():
        try:
            with open(image_path, 'rb') as f:
                img_data = f.read()
                
            msg_image = MIMEImage(img_data)
            # The CID (Content-ID) matches the src="cid:poster_img" in the HTML template
            msg_image.add_header('Content-ID', '<poster_img>')
            msg_image.add_header('Content-Disposition', 'inline', filename=Path(image_path).name)
            msg.attach(msg_image)
            print(f"  🖼️ Inline image embedded: {Path(image_path).name}")
        except Exception as e:
            print(f"  ⚠️ Failed to attach inline image: {e}")

    # Connect to SMTP server and send
    try:
        if SMTP_PORT == 465:
            server = smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT)
        else:
            server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
            server.starttls()  # Start TLS encryption
            
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.sendmail(sender, [recipient_email], msg.as_string())
        server.quit()
        print("  ✅ Email sent successfully!")
        return True, "sent"
    except Exception as e:
        print(f"  ❌ SMTP Error: {e}")
        return False, f"smtp_error: {str(e)}"

# A default marketing HTML template
def get_marketing_html_template(copy_text):
    """
    Wraps marketing copywriting text into a clean HTML format.
    Embeds the poster image if it has src="cid:poster_img".
    """
    # Replace newlines with <br> for HTML rendering
    formatted_copy = copy_text.replace('\n', '<br>')
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
                color: #333333;
                line-height: 1.6;
                background-color: #f4f6f8;
                margin: 0;
                padding: 20px;
            }}
            .card {{
                max-width: 600px;
                background: #ffffff;
                border-radius: 12px;
                box-shadow: 0 4px 10px rgba(0,0,0,0.05);
                padding: 30px;
                margin: 0 auto;
            }}
            .content {{
                font-size: 16px;
                margin-bottom: 25px;
            }}
            .image-container {{
                text-align: center;
                margin-top: 25px;
                border-radius: 8px;
                overflow: hidden;
            }}
            .image-container img {{
                max-width: 100%;
                height: auto;
                border-radius: 8px;
            }}
            .footer {{
                font-size: 12px;
                color: #888888;
                text-align: center;
                margin-top: 30px;
                border-top: 1px solid #eeeeee;
                padding-top: 15px;
            }}
        </style>
    </head>
    <body>
        <div class="card">
            <div class="content">
                {formatted_copy}
            </div>
            
            <!-- This refers to the inline attached image -->
            <div class="image-container">
                <img src="cid:poster_img" alt="醫師工具箱">
            </div>
            
            <div class="footer">
                © 2026 醫師工具箱. All rights reserved.
            </div>
        </div>
    </body>
    </html>
    """
    return html

if __name__ == "__main__":
    # Test sending to a mock address (uncomment and replace credentials to test)
    # os.environ["SMTP_USER"] = "your-email@gmail.com"
    # os.environ["SMTP_PASSWORD"] = "your-app-password"
    # test_copy = "🩺 看診對話，自動變成 SOAP 病歷\n\n歡迎免費體驗分享！"
    # test_html = get_marketing_html_template(test_copy)
    # send_marketing_email("recipient@example.com", "【醫師工具箱】AI 語音病歷生成器", test_html, "assets/doctor-toolbox-post.png")
    pass
