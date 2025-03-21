import globus_sdk

CLIENT_ID = "b4a71af8-6f1c-4f94-9da3-79103a9ebfe7"

# Authenticate interactively first (manual step):
native_client = globus_sdk.NativeAppAuthClient(CLIENT_ID)
native_client.oauth2_start_flow(
    requested_scopes=[
        "urn:globus:auth:scope:transfer.api.globus.org:all",
        "openid", "profile", "email"
    ]
)

authorize_url = native_client.oauth2_get_authorize_url()
print(f"Visit URL: {authorize_url}\n")

auth_code = input("Enter auth code: ").strip()
token_response = native_client.oauth2_exchange_code_for_tokens(auth_code)
transfer_token = token_response.by_resource_server["transfer.api.globus.org"]["access_token"]

# Create TransferClient
transfer_client = globus_sdk.TransferClient(
    authorizer=globus_sdk.AccessTokenAuthorizer(transfer_token)
)

# Define and create GCP endpoint
endpoint_doc = {
    "display_name": "My GCP Endpoint (Kubernetes)",
    "is_globus_connect": True,
    "DATA_TYPE": "endpoint"
}

endpoint = transfer_client.create_endpoint(endpoint_doc)

endpoint_id = endpoint["id"]
setup_key = endpoint["globus_connect_setup_key"]

print(f"Endpoint ID: {endpoint_id}")
print(f"GCP Setup Key (store securely): {setup_key}")
 