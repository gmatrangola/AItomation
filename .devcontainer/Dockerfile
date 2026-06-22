# .devcontainer/Dockerfile
FROM mcr.microsoft.com/devcontainers/python:3.11-bullseye

# Install a modern version of Node.js using the official NodeSource setup script
RUN apt-get update && apt-get install -y curl \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

RUN npm install -g @anthropic-ai/claude-code

# Enable corepack for pnpm support
RUN corepack enable

# Set up working directory
WORKDIR /workspace

# Install Python dependencies
COPY add-on/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Default command when the container starts
CMD ["sleep", "infinity"]
