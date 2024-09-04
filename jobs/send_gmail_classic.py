import smtplib
import os
from dotenv import load_dotenv

# load environment variables
load_dotenv()
GMAIL_USER = os.getenv("GMAIL_USER")
GMAIL_PASS = os.getenv("GMAIL_PASS")

def send_test_sms(number, carrier_email, message):
    recipient_email = f"{number}@{carrier_email}"

    print(f"Sending test message to {recipient_email}...")

    try:
        # set sender and password
        sender = GMAIL_USER
        password = GMAIL_PASS

        # create server object
        server = smtplib.SMTP("smtp.gmail.com", 587)  # Example for Gmail
        server.starttls()
        server.login(sender, password)

        # send message
        server.sendmail(sender, recipient_email, message)
        server.quit()
        print("Message sent successfully.")
        
    except smtplib.SMTPException as e:
        print(f"SMTP error occurred: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")

# Example usage: change this as needed for testing
test_number = "4043134793"  # replace with actual test number
carrier_email = "vzwpix.com"  # replace with correct carrier email domain
test_message = "Test message from the simplified script."

# Run the test
send_test_sms(test_number, carrier_email, test_message)