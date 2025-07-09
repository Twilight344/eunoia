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

# oauth_config.py
import os
from google.oauth2 import id_token
from google.auth.transport import requests

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")

def verify_google_token(id_token_str):
    """Verify Google ID token and return user info"""
    try:
        idinfo = id_token.verify_oauth2_token(
            id_token_str,
            requests.Request(),
            GOOGLE_CLIENT_ID
        )

        if idinfo['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
            raise ValueError('Wrong issuer.')

        if not idinfo.get('email_verified'):
            raise ValueError('Email not verified.')

        return {
            'email': idinfo['email'],
            'name': idinfo.get('name', ''),
            'picture': idinfo.get('picture', ''),
            'provider': 'google'
        }
    except Exception as e:
        print(f"[OAuth Error] Google token verification failed: {e}")
        return None

