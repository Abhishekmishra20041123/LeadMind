import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import asyncio
from db import companies_collection
from bson import ObjectId

class EmailService:
    @staticmethod
    async def send_email(company_id: str, to_address: str, subject: str, html_content: str):
        # 1. Get SMTP settings from company profile
        company = await companies_collection.find_one({"_id": ObjectId(company_id)})
        if not company:
            raise ValueError("Company not found")
            
        settings = company.get("settings", {})
        smtp_host = settings.get("smtp_host", os.getenv("SMTP_HOST", "smtp.gmail.com"))
        smtp_port = int(settings.get("smtp_port", os.getenv("SMTP_PORT", 587)))
        smtp_user = settings.get("smtp_user", os.getenv("SMTP_USER"))
        smtp_pass = settings.get("smtp_pass", os.getenv("SMTP_PASS"))
        from_email = settings.get("from_email", smtp_user or "noreply@strategicgrid.ai")
        from_name = settings.get("from_name", company.get("company_name", "Sales Agent"))
        
        if not smtp_user or not smtp_pass:
            # Fallback for local testing if SMTP isn't configured
            print(f"\n[MOCK EMAIL] To: {to_address} | Subject: {subject}")
            print(f"Content snippet: {html_content[:100]}...\n")
            await asyncio.sleep(1) # simulate network
            return True
            
        # 2. Construct message
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{from_name} <{from_email}>"
        msg["To"] = to_address
        
        part = MIMEText(html_content, "html")
        msg.attach(part)
        
        # 3. Send in thread using standard smtplib
        def _send():
            server = smtplib.SMTP(smtp_host, smtp_port)
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.sendmail(from_email, to_address, msg.as_string())
            server.quit()
            
        try:
            await asyncio.to_thread(_send)
            return True
        except Exception as e:
            print(f"Failed to send email via SMTP: {e}")
            raise ValueError(f"SMTP Error: {str(e)}")
