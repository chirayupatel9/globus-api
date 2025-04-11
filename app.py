import os
import json
from typing import Optional
import requests
import globus_sdk
from fastapi import FastAPI, Request, Response, HTTPException, Depends
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, BaseSettings
from starlette.middleware.sessions import SessionMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
import subprocess
from pathlib import Path
import shutil
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
CLIENT_ID = os.getenv("GLOBUS_CLIENT_ID") # CLIENT UUID from globus
CLIENT_SECRET = os.getenv("GLOBUS_CLIENT_SECRET") # CLIENT SECRET from globus
REDIRECT_URI = os.getenv("REDIRECT_URI", "http://localhost:5000/callback")
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


# 2. Create a dependency for transfer client
async def get_transfer_client(session: dict = Depends(get_session)):
    if "access_token" not in session:
        raise HTTPException(status_code=401, detail="User not authenticated")
    authorizer = globus_sdk.AccessTokenAuthorizer(session["access_token"])
    return globus_sdk.TransferClient(authorizer=authorizer)

# 3. Optimize endpoint routes using the new dependency
@app.get("/api/endpoints")
async def list_globus_endpoints(
    transfer_client: globus_sdk.TransferClient = Depends(get_transfer_client)
):
    """List the user's Globus endpoints using a valid filter"""
    try:
        endpoints = [
            {"id": ep["id"], "display_name": ep["display_name"]}
            for ep in transfer_client.endpoint_search(filter_scope="my-endpoints")
        ]
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

# 4. Optimize create_endpoint function
@app.post("/api/create-endpoint")
async def create_endpoint(
    endpoint: EndpointCreate,
    transfer_client: globus_sdk.TransferClient = Depends(get_transfer_client)
):
    
        # Step 1: Create the endpoint via Transfer API
        endpoint_doc = {
            "display_name": endpoint.display_name,
            "is_globus_connect": True,
            "DATA_TYPE": "endpoint"
        }
        result = transfer_client.create_endpoint(endpoint_doc)
        endpoint_id = result["id"]
        setup_key = result["globus_connect_setup_key"]

        # Step 2: Prepare environment
        env = os.environ.copy()
        env.update({
            "GCP_SETUP_KEY": setup_key,
            "GCP_USER": os.getenv("GCP_USER"),
            "GCP_OS_VERSION": "ubuntu22.04",
            "GCP_RELAY_SERVER": "relay.globusonline.org",
            "GCP_FTP_PORT": "50000",
            "GLOBUS_TCP_PORT_RANGE": "50000,51000",
            "GCP_CONFIG_DIR": "/home/gridftp/.globusonline",
            "GCP_GLOBAL_ETC_DIR": "/home/gridftp/globusconnectpersonal-3.2.6/etc",
            "GCP_GRIDFTP_PATH": "/home/gridftp/globusconnectpersonal-3.2.6/gt_amd64/bin/gridftp",
            "GCP_PDEATH_PATH": "/home/gridftp/globusconnectpersonal-3.2.6/gt_amd64/bin/pdeath",
            "GCP_SSH_PATH": "/usr/bin/ssh"
        })

        # Step 3: Create dummy gridftp binary if needed
        dummy_path = env["GCP_GRIDFTP_PATH"]
        dummy_dir = os.path.dirname(dummy_path)
        os.makedirs(dummy_dir, exist_ok=True)
        Path(dummy_path).touch()
        os.chmod(dummy_path, 0o755)

        # # Step 4: Run setup and start
        # subprocess.Popen(
        #     ["/home/gridftp/globusconnectpersonal-3.2.6/globusconnectpersonal", "-debug", "-setup", f"{setup_key}"],
        #     env=env)
        # subprocess.Popen(
        #         ["/home/gridftp/globusconnectpersonal-3.2.6/globusconnectpersonal", "-debug", "-start"],
        #     env=env
        # )
        # save the setup key and endpoint id to a single file
        with open("setup_key.txt", "w") as f:
            f.write(f"KEY1={endpoint_id}\nKEY2={setup_key}")
        return {
            "message": "Endpoint created and GCP started successfully",
            "endpoint_id": endpoint_id,
            "setup_key": setup_key
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000, debug=True)