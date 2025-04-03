FROM ubuntu:22.04

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HOME=/home/globus \
    GLOBUS_CONFIG_PATH=/home/globus/globus_config \
    GLOBUS_OPTIONAL_MODE=false \
    TERM=xterm

# Install necessary packages
RUN apt-get update && \
    apt-get install -y wget rsync openssh-client python3 python3-pip dos2unix&& \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* && \
    pip3 install --upgrade pip && \
    update-alternatives --install /usr/bin/python python /usr/bin/python3 1

# Create globus user and necessary directories
RUN adduser globus && \
    mkdir -p /home/globus/globus_config/.globus && \
    mkdir -p /home/globus/globus_config/.globusonline && \
    mkdir -p /home/globus/data && \
    mkdir -p /app

# Install Globus Connect Personal
RUN cd /root && \
    wget https://downloads.globus.org/globus-connect-personal/linux/stable/globusconnectpersonal-latest.tgz && \
    tar xzvf /root/globusconnectpersonal-latest.tgz -C /home/globus && \
    rm -f /root/globusconnectpersonal-latest.tgz

# Set up permissions
RUN chown -R globus:globus /home/globus && \
    chown -R globus:globus /app && \
    chmod -R 755 /home/globus/globus_config && \
    chmod -R 755 /home/globus/data 
    # Set working directory

WORKDIR /app


# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Ensure proper ownership of application files
RUN chown -R globus:globus /app

# Create volumes
VOLUME /home/globus/globus_config
VOLUME /home/globus/data

# Switch to non-root user
USER globus

# Expose the port the app runs on
EXPOSE 5000

RUN dos2unix initialize.sh
RUN dos2unix .env
RUN chmod +x initialize.sh

# Command to run the application
CMD ["python3", "run_with_ngrok.py"]
