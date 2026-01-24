#!/bin/bash

# Send sample report via email
# Usage: ./send_report.sh tod@vridhamma.org

RECIPIENT="${1:-tod@vridhamma.org}"
REPORT_FILE="volumes/reports/dpvc_weekly_20260116_to_20260123.pdf"

if [ ! -f "$REPORT_FILE" ]; then
    echo "❌ Report file not found: $REPORT_FILE"
    exit 1
fi

echo "Sending report to $RECIPIENT..."

# Try using sendmail if available
if command -v sendmail &> /dev/null; then
    {
        echo "To: $RECIPIENT"
        echo "From: admin@globalpagoda.org"
        echo "Subject: Feedback System - Sample Report (DPVC Weekly)"
        echo "MIME-Version: 1.0"
        echo "Content-Type: multipart/mixed; boundary=\"BOUNDARY\""
        echo ""
        echo "--BOUNDARY"
        echo "Content-Type: text/plain; charset=UTF-8"
        echo ""
        echo "Hello,"
        echo ""
        echo "This is a sample feedback report from the Pala Platform Feedback System."
        echo ""
        echo "The attached PDF contains feedback data for DPVC (Dhamma Pattana Vipassana Centre)"
        echo "covering the period from Jan 16 to Jan 23, 2026."
        echo ""
        echo "Report includes:"
        echo "- Total feedback submissions"
        echo "- Average ratings"
        echo "- Rating distribution"
        echo "- Individual feedback details with comments"
        echo ""
        echo "Best regards,"
        echo "Feedback System"
        echo ""
        echo "--BOUNDARY"
        echo "Content-Type: application/pdf; name=\"dpvc_weekly_report.pdf\""
        echo "Content-Transfer-Encoding: base64"
        echo "Content-Disposition: attachment; filename=\"dpvc_weekly_report.pdf\""
        echo ""
        base64 "$REPORT_FILE"
        echo ""
        echo "--BOUNDARY--"
    } | sendmail -t
    echo "✅ Email sent successfully to $RECIPIENT"
# Try using mail command
elif command -v mail &> /dev/null; then
    echo "Sending via mail command..."
    mail -s "Feedback System - Sample Report (DPVC Weekly)" -A "$REPORT_FILE" "$RECIPIENT" <<EOF
Hello,

This is a sample feedback report from the Pala Platform Feedback System.

The attached PDF contains feedback data for DPVC (Dhamma Pattana Vipassana Centre)
covering the period from Jan 16 to Jan 23, 2026.

Report includes:
- Total feedback submissions
- Average ratings
- Rating distribution
- Individual feedback details with comments

Best regards,
Feedback System
EOF
    echo "✅ Email sent successfully to $RECIPIENT"
else
    echo "❌ No mail command available (sendmail or mail)"
    echo ""
    echo "Alternative options:"
    echo "1. Install mailutils: sudo apt-get install mailutils"
    echo "2. Manually send the report from: $(pwd)/$REPORT_FILE"
    echo "3. Use this command to email it:"
    echo "   echo 'See attached' | mail -s 'Sample Report' -A $REPORT_FILE $RECIPIENT"
fi
