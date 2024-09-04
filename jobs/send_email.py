import os
import requests
from dotenv import load_dotenv
import json

# Load environment variables from .env file
load_dotenv()

# Get values from environment variables
ZOHO_EMAIL = os.getenv('ZOHO_EMAIL')
ZOHO_ACCOUNT_ID = os.getenv('ZOHO_ACCOUNT_ID')
ZOHO_REFRESH_TOKEN = os.getenv('ZOHO_REFRESH_TOKEN')
ZOHO_CLIENT_ID = os.getenv('ZOHO_CLIENT_ID')
ZOHO_CLIENT_SECRET = os.getenv('ZOHO_CLIENT_SECRET')

def refresh_access_token():
    url = "https://accounts.zoho.com/oauth/v2/token"
    data = {
        "refresh_token": ZOHO_REFRESH_TOKEN,
        "client_id": ZOHO_CLIENT_ID,
        "client_secret": ZOHO_CLIENT_SECRET,
        "grant_type": "refresh_token"
    }

    response = requests.post(url, data=data)

    if response.status_code == 200:
        new_access_token = response.json().get('access_token')
        print(f"New Access Token: {new_access_token}")

        # Optionally update the .env file with the new access token
        with open('.env', 'r') as file:
            env_vars = file.readlines()

        with open('.env', 'w') as file:
            for line in env_vars:
                if line.startswith('ZOHO_ACCESS_TOKEN'):
                    file.write(f'ZOHO_ACCESS_TOKEN={new_access_token}\n')
                else:
                    file.write(line)

        # Update the environment variable
        os.environ['ZOHO_ACCESS_TOKEN'] = new_access_token

        return new_access_token
    else:
        print(f"Failed to refresh access token: {response.status_code}")
        print(response.text)
        return None

def send_email_via_api(to_address, subject, content):
    
    # get fresh token
    access_token = refresh_access_token()
    if not access_token:
        print("Unable to refresh access token. Exiting...")
        return

    url = f"https://mail.zoho.com/api/accounts/{ZOHO_ACCOUNT_ID}/messages"
    headers = {
        "Authorization": f"Zoho-oauthtoken {access_token}",
        "Content-Type": "application/json"
    }
    payload = {
        "fromAddress": ZOHO_EMAIL,
        "toAddress": to_address,
        "subject": subject.strip(),
        "content": content.strip(),
        "mailFormat": "html"
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
test_email = "matttebbetts@gmail.com"
send_email_via_api(test_email, "Mini", "There's still time to do the Mini!")
