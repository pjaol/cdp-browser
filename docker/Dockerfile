FROM --platform=linux/arm64 browserless/chrome:latest

USER root

# Install Python and other dependencies
RUN apt-get update && apt-get install -y \
    curl \
    telnet \
    nodejs \
    npm \
    && rm -rf /var/lib/apt/lists/*
    

# Install http-proxy for reverse proxy
RUN npm install -g http-proxy
#RUN groupadd -r nobody
#RUN useradd -r -g nobody -d /home/nobody -s /bin/bash -c "Docker image user" nobody


# Expose browserless port
EXPOSE 9222
EXPOSE 9223

# Copy our custom startup script and proxy script
COPY docker/startup.sh ./startup.sh
COPY docker/proxy.js ./proxy.js
RUN chmod +x ./startup.sh

#USER nobody
# Use our custom startup script
CMD ["./startup.sh"] 