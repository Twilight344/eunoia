# import os
# from google.oauth2 import id_token
# from google.auth.transport import requests
# import jwt
# import json
# import requests as http_requests

# # Google OAuth Configuration
# GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')
# GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET')

# def verify_google_token(token):
#     """Verify Google ID token and return user info"""
#     try:
#         idinfo = id_token.verify_oauth2_token(
#             token, 
#             requests.Request(), 
#             GOOGLE_CLIENT_ID
#         )
        
#         if idinfo['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
#             raise ValueError('Wrong issuer.')
            
#         return {
#             'email': idinfo['email'],
#             'name': idinfo.get('name', ''),
#             'picture': idinfo.get('picture', ''),
#             'provider': 'google'
#         }
#     except Exception as e:
#         print(f"Google token verification failed: {e}")
#         return None 

import os
from google.oauth2 import id_token
from google.auth.transport import requests
import requests as http_requests

GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')
GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET')
GOOGLE_REDIRECT_URI = os.getenv('GOOGLE_REDIRECT_URI')

def exchange_code_for_tokens(code):
    """Exchange OAuth code for tokens from Google"""
    token_url = "https://oauth2.googleapis.com/token"
    data = {
        'code': code,
        'client_id': GOOGLE_CLIENT_ID,
        'client_secret': GOOGLE_CLIENT_SECRET,
        'redirect_uri': GOOGLE_REDIRECT_URI,
        'grant_type': 'authorization_code'
    }

    response = http_requests.post(token_url, data=data)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"[ERROR] Token exchange failed: {response.text}")
        return None

def verify_google_token(id_token_str):
    """Verify Google ID token and return user info"""
    try:
        idinfo = id_token.verify_oauth2_token(
            id_token_str,
            requests.Request(),
            GOOGLE_CLIENT_ID
        )

        if idinfo['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
            raise ValueError('Invalid issuer.')

        return {
            'email': idinfo['email'],
            'name': idinfo.get('name', ''),
            'picture': idinfo.get('picture', ''),
            'provider': 'google'
        }

    except Exception as e:
        print(f"[ERROR] ID Token verification failed: {e}")
        return None
