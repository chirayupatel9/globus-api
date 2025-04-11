FROM rockylinux:9

VOLUME /home/gridftp/globus_config
VOLUME /home/gridftp/data 

# Install necessary packages
RUN yum -y update && \
    yum -y install wget rsync openssh-clients python pip dos2unix  && \
    yum -y install epel-release && \
    yum -y update && \
    dnf -y install https://dl.fedoraproject.org/pub/epel/epel-release-latest-9.noarch.rpm && \
    pip3 install --upgrade globus-cli && \
    adduser gridftp

    
RUN cd /root && \
    wget https://downloads.globus.org/globus-connect-personal/linux/stable/globusconnectpersonal-latest.tgz && \
    tar xzvf /root/globusconnectpersonal-latest.tgz -C /home/gridftp && \
    chown -R gridftp.gridftp /home/gridftp/globus* 

# Create directories and adjust permissions
RUN mkdir -p /home/gridftp/globus_config/.globus && \
    mkdir -p /home/gridftp/globus_config/.globusonline && \
    mkdir -p /home/gridftp/data && \
    chown -R gridftp:gridftp /home/gridftp/globus_config && \
    chown -R gridftp:gridftp /home/gridftp/data && \
    chmod -R 755 /home/gridftp/globus_config && \
    chmod -R 755 /home/gridftp/data

# Copy the script into the container
COPY globus-connect-personal.sh /home/gridftp/globus-connect-personal.sh
COPY initialization.sh /home/gridftp/initialization.sh
COPY entrypoint.sh /home/gridftp/entrypoint.sh
COPY run_with_ngrok.py /home/gridftp/run_with_ngrok.py
COPY app.py /home/gridftp/app.py
COPY .env /home/gridftp/.env
COPY requirements.txt /home/gridftp/requirements.txt

RUN pip3 install -r /home/gridftp/requirements.txt
# Make the script executable
RUN chmod +x /home/gridftp/initialization.sh /home/gridftp/entrypoint.sh /home/gridftp/globus-connect-personal.sh
# Convert Windows line endings to Unix
RUN dos2unix /home/gridftp/initialization.sh /home/gridftp/entrypoint.sh /home/gridftp/globus-connect-personal.sh
# globus-connect-server-setup script needs these
ENV HOME=/root
ENV TERM=xterm


# Set environment variables
ENV HOME=/home/gridftp
ENV GLOBUS_CONFIG_PATH=/home/gridftp/globus_config
ENV GLOBUS_OPTIONAL_MODE=false  

CMD ["chmod -R 777 /shared-data"]
# Set entrypoint to run on startup 
ENTRYPOINT ["/home/gridftp/entrypoint.sh"]
