import os
from pyngrok import ngrok
import uvicorn
import json

# Your ngrok auth token (get it from https://dashboard.ngrok.com/auth)
NGROK_AUTH_TOKEN = "2uaYpvdLtzRnlHxaz8GHhYcxW7Q_NoU1GnbabFNTgV3Hxb5L"

def update_redirect_uri(ngrok_url):
    """Update the REDIRECT_URI in app.py with the new ngrok URL"""
    with open('app.py', 'r') as file:
        content = file.read()
    
    # Update the REDIRECT_URI
    new_redirect_uri = f"{ngrok_url}/callback"
    content = content.replace(
        'REDIRECT_URI = "' + content.split('REDIRECT_URI = "')[1].split('"')[0] + '"',
        f'REDIRECT_URI = "{new_redirect_uri}"'
    )
    
    with open('app.py', 'w') as file:
        file.write(content)

def run_app():
    # Configure ngrok
    ngrok.set_auth_token(NGROK_AUTH_TOKEN)
    
    # Start ngrok tunnel
    public_url = ngrok.connect(5000).public_url
    
    # Convert http to https
    if public_url.startswith('http://'):
        public_url = 'https://' + public_url[7:]
    
    print(f"NGrok URL: {public_url}")
    
    # Update the redirect URI in app.py
    update_redirect_uri(public_url)
    
    # Start the FastAPI app
    uvicorn.run("app:app", host="0.0.0.0", port=5000, reload=True)

if __name__ == "__main__":
    run_app() 