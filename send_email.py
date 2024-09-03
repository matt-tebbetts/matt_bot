import os
import requests
from dotenv import load_dotenv
import json

# Load environment variables from .env file
load_dotenv()

# Get values from environment variables
access_token = os.getenv('ZOHO_ACCESS_TOKEN')
zoho_email = os.getenv('ZOHO_EMAIL')
zoho_account_id = os.getenv('ZOHO_ACCOUNT_ID')

def send_email_via_api(to_address, subject, content):
    url = f"https://mail.zoho.com/api/accounts/{zoho_account_id}/messages"
    headers = {
        "Authorization": f"Zoho-oauthtoken {access_token}",
        "Content-Type": "application/json"
    }
    payload = {
        "fromAddress": zoho_email,           # Must be associated with your Zoho account
        "toAddress": to_address,             # Valid recipient email address
        "subject": subject.strip(),          # Strip to avoid leading/trailing spaces
        "content": content.strip(),          # Strip to avoid leading/trailing spaces
        "mailFormat": "html"                 # Use "html" or "plaintext"
    }

    # Convert the payload to JSON
    payload_json = json.dumps(payload, ensure_ascii=False)

    # Print the URL, headers, and payload for debugging
    print("Debug Info:")
    print(f"URL: {url}")
    print(f"Headers: {headers}")
    print(f"Payload: {payload_json}")

    try:
        response = requests.post(url, data=payload_json, headers=headers)

        # Print the response status code and text
        print(f"Response Status Code: {response.status_code}")
        print(f"Response Text: {response.text}")

        if response.status_code != 200:
            print("Failed to send email. The API might be expecting a different pattern.")
            print(f"Error Details: {response.json()}")

    except requests.exceptions.RequestException as e:
        # Print any exception that occurs during the request
        print(f"An error occurred: {e}")

# Example usage
test_email = "4043134793@vtext.com"
send_email_via_api(test_email, "Test Subject", "This is a test email.")
