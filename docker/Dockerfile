FROM browserless/chrome:latest

USER root

# Install required packages
RUN apt-get update && apt-get install -y \
    curl \
    telnet \
    nodejs \
    npm

# Install http-proxy globally
RUN npm install -g http-proxy

# Copy our custom startup script and proxy script
COPY startup.sh ./startup.sh
COPY proxy.js ./proxy.js
RUN chmod +x ./startup.sh

# Set environment variables
ENV PORT=9223
ENV CHROME_PORT=3000

# Expose the proxy port
EXPOSE 9223

# Start the proxy
CMD ["./startup.sh"] 