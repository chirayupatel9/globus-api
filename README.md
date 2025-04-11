### Globus container
- Build globus container
- docker build -t globus_container -f Dockerfile .

{Below Command is for windows CLI}
```bash
docker run -e DataPath="E:/globus_data/data" -e ConfigPath="E:/globus_data/config" -v "E:/globus_data/config:/home/gridftp/globus_config" -v "E:/globus_data/data:/home/gridftp/data" -it globus
```
```bash
docker run -e DataPath="E://globus_data//data" -e ConfigPath="E://globus_data//config" -v "E://globus_data//config:/home/gridftp/globus_config" -v "E://globus_data//data:/home/gridftp/data" -e START_GLOBUS="true" -it globus
```
- setup globus with login and set a endpoint

## Setup a thick client in globus
### Copy the UUID and its secret 
### Add Ngrok auth in env

```bash
clear;docker build -t globus .;docker run -it globus
```