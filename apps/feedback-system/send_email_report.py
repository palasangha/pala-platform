#!/usr/bin/env python3
"""
Send feedback report via email using Gmail SMTP or local SMTP server
"""
import smtplib
import sys
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from pathlib import Path

# Configuration
REPORT_PATH = "volumes/reports/dpvc_weekly_20260116_to_20260123.pdf"
RECIPIENT = "tod@vridhamma.org"
SENDER = "admin@globalpagoda.org"
SUBJECT = "Feedback System - Sample Report (DPVC Weekly)"

BODY = """Hello,

This is a sample feedback report from the Pala Platform Feedback System.

The attached PDF contains feedback data for DPVC (Dhamma Pattana Vipassana Centre)
covering the period from Jan 16 to Jan 23, 2026.

Report includes:
- Total feedback submissions: 10
- Average rating: 7.8/10
- Rating distribution across categories
- Individual feedback with comments
- Anonymous and identified submissions

This report was generated automatically by the system and demonstrates
the weekly reporting capability of the feedback platform.

Best regards,
Feedback System
Global Vipassana Pagoda
"""

def send_email():
    report_file = Path(REPORT_PATH)
    
    if not report_file.exists():
        print(f"❌ Error: Report file not found: {REPORT_PATH}")
        return False
    
    # Create message
    msg = MIMEMultipart()
    msg['From'] = SENDER
    msg['To'] = RECIPIENT
    msg['Subject'] = SUBJECT
    
    # Attach body
    msg.attach(MIMEText(BODY, 'plain'))
    
    # Attach PDF
    with open(report_file, 'rb') as f:
        pdf = MIMEApplication(f.read(), _subtype='pdf')
        pdf.add_header('Content-Disposition', 'attachment', 
                      filename='dpvc_weekly_report.pdf')
        msg.attach(pdf)
    
    print(f"📧 Attempting to send report to {RECIPIENT}...")
    print(f"📎 Report: {report_file.name} ({report_file.stat().st_size} bytes)")
    
    # Try different SMTP methods
    methods = [
        ("localhost", 25, None, None),
        ("localhost", 587, None, None),
    ]
    
    for smtp_host, smtp_port, username, password in methods:
        try:
            print(f"   Trying {smtp_host}:{smtp_port}...")
            server = smtplib.SMTP(smtp_host, smtp_port, timeout=5)
            
            if smtp_port == 587:
                server.starttls()
            
            if username and password:
                server.login(username, password)
            
            server.send_message(msg)
            server.quit()
            
            print(f"✅ Email sent successfully to {RECIPIENT}")
            print(f"   Server: {smtp_host}:{smtp_port}")
            return True
            
        except Exception as e:
            print(f"   Failed: {str(e)[:60]}")
            continue
    
    print("\n❌ Could not send email - no SMTP server available")
    print("\n📋 Alternative options:")
    print(f"1. Manually send the report from:")
    print(f"   {report_file.absolute()}")
    print(f"\n2. Copy to your local machine:")
    print(f"   scp user@host:{report_file.absolute()} ~/Downloads/")
    print(f"\n3. View the PDF locally:")
    print(f"   xdg-open {REPORT_PATH}")
    
    return False

if __name__ == "__main__":
    if len(sys.argv) > 1:
        RECIPIENT = sys.argv[1]
    
    send_email()
