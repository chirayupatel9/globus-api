#!/bin/bash

# # Assign input arguments to variables
# DataPath=$1
# ConfigPath=$2

# Inside the container: Setup the Globus Personal Endpoint
# globus login --no-local-server

# # Collect information about the endpoint
# endpoint_info=$(globus endpoint create --personal myep 2>&1)

# Extract the Endpoint ID and Setup Key from the output
export GCP_DEBUG=1 
endpoint_id=$KEY1
setup_key=$KEY2

# Set the environment variables
export GLOBUS_ENDPOINT_ID="$endpoint_id"
export GLOBUS_SETUP_KEY="$setup_key"
[...]
# Change to the Globus Connect Personal directory
cd /home/gridftp/globusconnectpersonal-*/

# DEBUG
echo '=============================================================================================='
echo "Preparing to test connectivity from within initialization.sh."
echo -e "-------------------------------------------------------------\n"
echo -e "Testing auth.globus.org:\n"
curl -vk https://auth.globus.org
echo -e "Testing relay.globusonline.org:\n"
nc relay.globusonline.org 2223 -w 2
echo "Preparing to execute: ./globusconnectpersonal -debug -setup --setup-key $GLOBUS_SETUP_KEY"
echo '=============================================================================================='
# DEBUG

# Finish the Endpoint Setup
strace -s1024 -F ./globusconnectpersonal -debug -setup $GLOBUS_SETUP_KEY

# Copy the Globus configuration to the host directory
cp -p -r /home/gridftp/.globus* /home/gridftp/globus_config

./globusconnectpersonal -debug -start &
echo "/home/gridftp/data,0,1" >> ~/.globusonline/lta/config-paths

# Copy the Globus configuration to the host directory
cp -p -r /home/gridftp/.globus* /home/gridftp/globus_config