import os
from pyngrok import ngrok
import uvicorn
import json

def run_app():
    # Configure ngrok
    ngrok_token = "2vXiWT7jNWD6YE3NJBreUcu8pOF_3cEom2NzNvPny3Z2Vasic"#os.getenv("NGROK_AUTH_TOKEN")
    if not ngrok_token:
        raise ValueError("NGROK_AUTH_TOKEN environment variable is not set")
    
    ngrok.set_auth_token(ngrok_token)
    
    # Start ngrok tunnel
    public_url = ngrok.connect(5000).public_url
    
    # Convert http to https
    if public_url.startswith('http://'):
        public_url = 'https://' + public_url[7:]
    
    print(f"NGrok URL: {public_url}")
    
    # Set the REDIRECT_URI environment variable
    os.environ["REDIRECT_URI"] = f"{public_url}/callback"
    
    # Start the FastAPI app
    uvicorn.run("app:app", host="0.0.0.0", port=5000, reload=True)

if __name__ == "__main__":
    run_app() 