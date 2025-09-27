# syntax=docker/dockerfile:1
ARG BUILD_FROM

# --- Builder Stage with better caching ---
FROM node:20-alpine AS builder

# Install pnpm first (this layer rarely changes)
RUN npm install -g pnpm

WORKDIR /usr/src/app

# Copy dependency files first (for better Docker layer caching)
COPY src/frontend/package.json src/frontend/pnpm-lock.yaml ./

# Install dependencies (this layer is cached if deps don't change)
RUN pnpm install --frozen-lockfile --reporter=append-only

# Copy source and build (only this layer rebuilds when code changes)
COPY src/frontend/ ./
RUN pnpm build

# --- Final Stage ---
FROM ${BUILD_FROM}

WORKDIR /usr/src/app

# Install Python deps (cache this layer)
COPY requirements.txt ./
RUN apk add --no-cache python3 py3-pip && \
    pip3 install --no-cache-dir --break-system-packages -r requirements.txt

# Copy backend code
COPY src/backend/ ./src/backend/

# Copy pre-built frontend
COPY --from=builder /usr/src/app/dist ./src/backend/dist

# Copy service files
RUN mkdir -p /etc/services.d/aitomations
COPY run.sh /etc/services.d/aitomations/run
RUN chmod +x /etc/services.d/aitomations/run

COPY rootfs/ /

EXPOSE 8099