#!/bin/bash
# Load .env file
set -o allexport
source .env
set +o allexport

# echo "Loaded DataPath = $DataPath"
# echo "Loaded SETUP_KEY = $SETUP_KEY"

# Create the data directory if it doesn't exist
mkdir -p "~/DataPath"
whoami

sleep 10

cd /home/globus/globusconnectpersonal-*/
echo "Setup starting"
/home/globus/globusconnectpersonal-3.2.6/globusconnectpersonal -debug -setup $SETUP_KEY || {
    echo "Globus setup failed, check /home/globus/.globusonline/lta/register.log"
    cat /home/globus/.globusonline/lta/register.log
    exit 1
}
echo "Setup complete"
sleep 10
command -v python3

# Copy the Globus configuration to the host directory
cp -p -r /home/globus/.globus* /home/globus/globus_config

echo "Starting Globus Connect Personal"
/home/globus/globusconnectpersonal-3.2.6/globusconnectpersonal -start &
echo "Globus Connect Personal started"

echo "/home/globus/data,0,1" >> ~/.globusonline/lta/config-paths

echo "Copying Globus configuration to host directory"
cp -p -r /home/globus/.globus* /home/globus/globus_config

echo "Initialization complete"
