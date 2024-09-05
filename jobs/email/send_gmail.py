import smtplib
from email.mime.text import MIMEText
import os
from dotenv import load_dotenv

load_dotenv()

def send_email_gmail(to_address, subject, content):
    gmail_user = os.getenv('GMAIL_USER')
    gmail_pass = os.getenv('GMAIL_PASS')

    msg = MIMEText(content)
    msg['Subject'] = subject
    msg['From'] = gmail_user
    msg['To'] = to_address

    try:
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(gmail_user, gmail_pass)
        server.sendmail(gmail_user, [to_address], msg.as_string())
        server.quit()
        print("Email sent successfully!")
    except Exception as e:
        print(f"Error sending email: {e}")

test_email = "4043134793@vtext.com"
send_email_gmail(test_email, "Test Subject", "This is a test email")