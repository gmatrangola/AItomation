# add-on/Dockerfile
ARG BUILD_FROM
FROM $BUILD_FROM

# Set environment variables for non-interactive installs
ENV DEBIAN_FRONTEND=noninteractive

# Install Python and Node.js dependencies for the add-on
# This is a minimal set. Add any other system dependencies needed by your Python packages.
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    nodejs \
    npm \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy Python requirements and install them
COPY requirements.txt /tmp/requirements.txt
RUN pip3 install --no-cache-dir -r /tmp/requirements.txt

# Copy add-on scripts and rootfs
COPY run.sh /
COPY rootfs/ /

# Set up working directory for frontend build
WORKDIR /app/frontend

# Copy frontend source and build it
COPY src/frontend/package.json src/frontend/package-lock.json ./
RUN npm install --production=false # Install dev dependencies for build
COPY src/frontend/ .
RUN npm run build # Build the Vue app

# Move the built frontend to the backend's static directory
RUN mv dist /app/backend/static

# Clean up npm cache and dev dependencies
RUN npm cache clean --force && rm -rf node_modules

# Set working directory for backend
WORKDIR /app/backend

# Copy backend source
COPY src/backend/ .

# Ensure run.sh is executable
RUN chmod +x /run.sh

# Expose port (as defined in config.json)
EXPOSE 8099

# Command to run the add-on
CMD ["/run.sh"]
