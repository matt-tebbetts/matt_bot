import os
import requests
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get the access token
access_token = os.getenv('ZOHO_ACCESS_TOKEN')

# API endpoint to retrieve all account details
url = "https://mail.zoho.com/api/accounts"

# Set the authorization header with the access token
headers = {
    "Authorization": f"Zoho-oauthtoken {access_token}",
    "Content-Type": "application/json"
}

# Make the GET request to fetch account details
response = requests.get(url, headers=headers)

if response.status_code == 200:
    accounts = response.json().get('data')
    for account in accounts:
        print(f"Account ID: {account['accountId']}, Email: {account['emailAddress']}")
else:
    print(f"Failed to retrieve account details: {response.status_code}")
    print(response.text)
