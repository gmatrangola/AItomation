# syntax=docker/dockerfile:1

# Declare BUILD_FROM globally, before any FROM statements.
ARG BUILD_FROM

# --- Builder Stage ---
# This stage builds the Vue frontend
# We use a standard node image and install pnpm to ensure cache invalidation.
FROM node:20-alpine AS builder

# Install pnpm
RUN npm install -g pnpm

WORKDIR /usr/src/app

# Copy only the necessary package manager files
COPY src/frontend/package.json src/frontend/pnpm-lock.yaml ./

# Install dependencies. This step is cached as long as lock file doesn't change.
RUN pnpm install --reporter=append-only

# Copy the rest of the frontend source code
COPY src/frontend/ ./

# Build the static assets
RUN pnpm build


# --- Final Stage ---
# This stage builds the final, lean add-on image
FROM ${BUILD_FROM}

WORKDIR /usr/src/app

# Install system dependencies for the Python backend
RUN apk add --no-cache \
    python3 \
    py3-pip

# Copy the requirements file first to leverage Docker cache
COPY requirements.txt ./

# Copy Python dependencies and install them
RUN pip3 install \
    --no-cache-dir \
    --break-system-packages \
    -r requirements.txt

# Copy the Python backend source code
COPY src/backend/ ./backend/

# Copy the pre-built frontend from the 'builder' stage
COPY --from=builder /usr/src/app/dist ./backend/dist

# Create the service directory and copy the run script
RUN mkdir -p /etc/services.d/aitomations
COPY run.sh /etc/services.d/aitomations/run
RUN chmod +x /etc/services.d/aitomations/run

# Copy rootfs contents
COPY rootfs/ /

# Set the current working directory to the backend
WORKDIR /usr/src/app/backend

# Expose the port the backend will run on
EXPOSE 8099

# The base image already has the correct ENTRYPOINT set up