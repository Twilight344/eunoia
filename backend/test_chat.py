
'''THIS SCRIPT IS ONLY FOR TESTING PURPOSES AND PLAYS NO ROLE IN THE WEBAPP'''
import requests

API_URL = "http://localhost:5000/chat"

while True:
    user_input = input("You: ")
    if user_input.lower() in ["exit", "quit"]:
        break

    payload = {"message": user_input}
    response = requests.post(API_URL, json=payload)
    