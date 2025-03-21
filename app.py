import os
import json
from typing import Optional
import requests
import globus_sdk
from fastapi import FastAPI, Request, Response, HTTPException, Depends
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from starlette.middleware.sessions import SessionMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
import subprocess
from pathlib import Path


# Initialize FastAPI App
app = FastAPI()

# Add CORS middleware with more specific configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add TrustedHost middleware to handle ngrok domain
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"]  # In production, replace with specific domains
)

# Add session middleware
app.add_middleware(
    SessionMiddleware,
    secret_key="super_secret_key"
)

# Get configuration from environment variables
CLIENT_ID = os.getenv("GLOBUS_CLIENT_ID")
CLIENT_SECRET = os.getenv("GLOBUS_CLIENT_SECRET")
REDIRECT_URI = "/callback"  # Will be set dynamically by run_with_ngrok.py
SCOPES = "urn:globus:auth:scope:transfer.api.globus.org:all"

# Create a ConfidentialAppAuthClient for token exchange
auth_client = globus_sdk.ConfidentialAppAuthClient(CLIENT_ID, CLIENT_SECRET)

# Pydantic models for request/response validation
class EndpointCreate(BaseModel):
    display_name: str
    description: Optional[str] = ""
    contact_email: Optional[str] = "admin@example.com"
    contact_info: Optional[str] = ""
    public: Optional[bool] = False
    organization: Optional[str] = "My Organization"

# Helper function to get session
async def get_session(request: Request):
    return request.session

@app.get("/")
async def home(session: dict = Depends(get_session)):
    """Home Route: Redirect to authentication"""
    if "access_token" in session:
        return {"message": "Authenticated!", "logout_url": "/logout"}
    return RedirectResponse(url="/login")

@app.get("/login")
async def login(session: dict = Depends(get_session)):
    """Initiate OAuth login and start OAuth2 flow"""
    auth_client.oauth2_start_flow(redirect_uri=REDIRECT_URI, requested_scopes=SCOPES)
    session["oauth_state"] = "started"
    
    globus_auth_url = auth_client.oauth2_get_authorize_url()
    return RedirectResponse(url=globus_auth_url)

@app.get("/callback")
async def callback(code: str, request: Request, session: dict = Depends(get_session)):
    """Handle OAuth callback and exchange code for tokens"""
    if "oauth_state" not in session:
        raise HTTPException(status_code=400, detail="OAuth flow not started. Please initiate login again.")
    
    if not code:
        raise HTTPException(status_code=400, detail="No authorization code provided!")

    try:
        auth_client.oauth2_start_flow(redirect_uri=REDIRECT_URI, requested_scopes=SCOPES)
        token_response = auth_client.oauth2_exchange_code_for_tokens(code)
        
        tokens = token_response.by_resource_server["transfer.api.globus.org"]
        session["access_token"] = tokens["access_token"]
        session["refresh_token"] = tokens["refresh_token"]
        session["expires_at"] = tokens["expires_at_seconds"]
        
        return RedirectResponse(url="/")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"OAuth token exchange failed: {str(e)}")

@app.get("/refresh")
async def refresh(session: dict = Depends(get_session)):
    """Automatically refresh expired access tokens"""
    if "refresh_token" not in session:
        return RedirectResponse(url="/login")
    
    try:
        token_response = auth_client.oauth2_refresh_token(session["refresh_token"])
        session["access_token"] = token_response["access_token"]
        session["expires_at"] = token_response["expires_at_seconds"]
        return RedirectResponse(url="/")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Token refresh failed: {str(e)}")

@app.get("/logout")
async def logout(session: dict = Depends(get_session)):
    """Logout and clear session"""
    session.clear()
    return RedirectResponse(url="/")

@app.get("/api/endpoints")
async def list_globus_endpoints(session: dict = Depends(get_session)):
    """List the user's Globus endpoints using a valid filter"""
    if "access_token" not in session:
        raise HTTPException(status_code=401, detail="User not authenticated")

    authorizer = globus_sdk.AccessTokenAuthorizer(session["access_token"])
    transfer_client = globus_sdk.TransferClient(authorizer=authorizer)

    try:
        endpoints = []
        for ep in transfer_client.endpoint_search(filter_scope="my-endpoints"):
            endpoints.append({"id": ep["id"], "display_name": ep["display_name"]})
        return {"endpoints": endpoints}
    except globus_sdk.GlobusAPIError as e:
        raise HTTPException(status_code=400, detail=f"Failed to list endpoints: {str(e)}")

@app.get("/api/endpoint/{endpoint_id}")
async def get_endpoint_details(endpoint_id: str, session: dict = Depends(get_session)):
    """Retrieve details of a specific endpoint"""
    if "access_token" not in session:
        raise HTTPException(status_code=401, detail="User not authenticated")

    authorizer = globus_sdk.AccessTokenAuthorizer(session["access_token"])
    transfer_client = globus_sdk.TransferClient(authorizer=authorizer)

    try:
        endpoint = transfer_client.get_endpoint(endpoint_id)
        return endpoint.data
    except globus_sdk.GlobusAPIError as e:
        raise HTTPException(status_code=400, detail=f"Failed to retrieve endpoint: {str(e)}")

@app.post("/api/create-endpoint")
async def create_endpoint(endpoint: EndpointCreate, session: dict = Depends(get_session)):
    """Create a new Globus endpoint using EndpointDocument"""
    if "access_token" not in session:
        raise HTTPException(status_code=401, detail="User not authenticated")

    authorizer = globus_sdk.AccessTokenAuthorizer(session["access_token"])
    transfer_client = globus_sdk.TransferClient(authorizer=authorizer)

    endpoint_doc = {
    "display_name": "My GCP Endpoint (Kubernetes)",
    "is_globus_connect": True,
    "DATA_TYPE": "endpoint"
}


    try:    
        endpoint_result = transfer_client.create_endpoint(endpoint_doc)
        ep = globus_sdk.response.GlobusHTTPResponse(response=endpoint_result) 
        endpoint_id = endpoint_result["id"]
        setup_key = endpoint_result["globus_connect_setup_key"]

        # Define GCP directory and binary path
        gcp_dir = Path.home() / "globus-connect-personal"
        gcp_bin = gcp_dir / "globusconnectpersonal"

        # Step 1: Download GCP if missing
        if not gcp_bin.exists():
            gcp_dir.mkdir(exist_ok=True)
            gcp_url = "https://downloads.globus.org/globus-connect-personal/linux/stable/globusconnectpersonal-latest.tgz"

            subprocess.run(["curl", "-L", "-o", "gcp.tgz", gcp_url], cwd=gcp_dir, check=True)
            subprocess.run(["tar", "xvzf", "gcp.tgz"], cwd=gcp_dir, check=True)
            subprocess.run(["chmod", "+x", "globusconnectpersonal"], cwd=gcp_dir, check=True)

        # Step 2: Run setup
        subprocess.run([str(gcp_bin), "-setup", setup_key], cwd=gcp_dir, check=True)

        # Step 3: Start GCP in background
        subprocess.Popen([str(gcp_bin)], cwd=gcp_dir)

        return {
            "message": "Endpoint created and GCP started successfully",
            "endpoint_id": endpoint_id,
            "setup_key": setup_key
        }

    except globus_sdk.GlobusAPIError as e:
        raise HTTPException(status_code=400, detail=f"Failed to create endpoint: {str(e)}")
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=f"GCP setup failed: {e}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000, debug=True)