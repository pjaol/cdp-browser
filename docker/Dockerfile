FROM --platform=linux/arm64 browserless/chrome:latest

USER root

# Install Python and other dependencies
RUN apt-get update && apt-get install -y \
    python3-pip \
    python3-venv \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN curl -sSL https://install.python-poetry.org | python3 -
ENV PATH="/root/.local/bin:$PATH"

# Create a directory for our Python application
RUN mkdir -p /app
WORKDIR /app

# Copy project files
COPY pyproject.toml poetry.lock* ./

# Install dependencies
RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi --without dev --no-root

# Copy the rest of the application
COPY . .

# Expose browserless port
EXPOSE 3000

# Return to the original working directory
WORKDIR /usr/src/app

# Copy our custom startup script
COPY docker/entrypoint.sh ./startup.sh
RUN chmod +x ./startup.sh

# Use our custom startup script
CMD ["./startup.sh"] 