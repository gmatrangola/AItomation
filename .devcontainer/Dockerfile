# .devcontainer/Dockerfile
FROM mcr.microsoft.com/devcontainers/python:3.11-bullseye

# Install a modern version of Node.js using the official NodeSource script
RUN apt-get update -y && apt-get install -y \
    ca-certificates \
    curl \
    gnupg \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

RUN corepack enable

# Set up working directory
WORKDIR /workspace

# Install Python dependencies (from requirements.txt, which will be copied into the container)
COPY ../requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt


# Expose ports (handled by devcontainer.json's forwardPorts)
# EXPOSE 8099
# EXPOSE 5173

# Default command when the container starts (can be overridden by devcontainer.json)
CMD ["sleep", "infinity"]
