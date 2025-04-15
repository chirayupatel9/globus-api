#!/bin/bash

# # Assign input arguments to variables
# DataPath=$1
# ConfigPath=$2

# Inside the container: Setup the Globus Personal Endpoint
# globus login --no-local-server

# # Collect information about the endpoint
# endpoint_info=$(globus endpoint create --personal myep 2>&1)

# Extract the Endpoint ID and Setup Key from the output
endpoint_id=$KEY1
setup_key=$KEY2

# Set the environment variables
export GLOBUS_ENDPOINT_ID="$endpoint_id"
export GLOBUS_SETUP_KEY="$setup_key"
whoami
echo "GLOBUS_ENDPOINT_ID=$GLOBUS_ENDPOINT_ID"
echo "GLOBUS_SETUP_KEY=$GLOBUS_SETUP_KEY"

# Change to the Globus Connect Personal directory
cd /home/gridftp/globusconnectpersonal-*/

# Finish the Endpoint Setup
./globusconnectpersonal -debug -setup --setup-key $GLOBUS_SETUP_KEY

# Copy the Globus configuration to the host directory
cp -p -r /home/gridftp/.globus* /home/gridftp/globus_config

./globusconnectpersonal -debug -start &
echo "/home/gridftp/data,0,1" >> ~/.globusonline/lta/config-paths

# Copy the Globus configuration to the host directory
cp -p -r /home/gridftp/.globus* /home/gridftp/globus_config