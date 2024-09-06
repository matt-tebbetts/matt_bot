import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get values from environment variables
authorization_code = os.getenv('ZOHO_AUTHORIZATION_CODE')
client_id = os.getenv('ZOHO_CLIENT_ID')
client_secret = os.getenv('ZOHO_CLIENT_SECRET')
redirect_uri = 'http://localhost'  # or use the redirect URI you set up

# Construct the curl command as a string
curl_command = f"""
curl --request POST \\
--url 'https://accounts.zoho.com/oauth/v2/token' \\
--header 'Content-Type: application/x-www-form-urlencoded' \\
--data 'code={authorization_code}&client_id={client_id}&client_secret={client_secret}&redirect_uri={redirect_uri}&grant_type=authorization_code'
"""

# Print the curl command
print("Run the following curl command in your terminal:")
print(curl_command)
