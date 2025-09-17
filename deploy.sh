#!/bin/bash

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
ADDON_NAME="aitomations"
HA_HOST="ha-dev.local"
REMOTE_USER="root"
REMOTE_PATH="/addons/${ADDON_NAME}"
LOCAL_PATH="/workspace/${ADDON_NAME}"
WORKSPACE_PATH="/workspace"

echo -e "${GREEN}🚀 Deploying AItomations Add-on${NC}"

# Function to print colored status
print_status() {
    echo -e "${YELLOW}➤${NC} $1"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

# Step 1: Build frontend and copy to backend
if [ -d "${LOCAL_PATH}/src/frontend" ]; then
    print_status "Building frontend..."
    cd "${LOCAL_PATH}/src/frontend"
    
    if [ -f "package.json" ]; then
        # Check if node_modules exists, if not install dependencies
        if [ ! -d "node_modules" ]; then
            print_status "Installing frontend dependencies..."
            pnpm install
        fi
        
        print_status "Building Vue.js frontend..."
        pnpm build
        
        # Copy built frontend to backend directory
        print_status "Copying built frontend to backend..."
        mkdir -p "${LOCAL_PATH}/src/backend/dist"
        cp -r dist/* "${LOCAL_PATH}/src/backend/dist/"
        
        print_success "Frontend built and copied successfully"
        
        # Show what was copied
        print_status "Built frontend files:"
        ls -la "${LOCAL_PATH}/src/backend/dist/"
    else
        print_error "No package.json found in frontend directory"
        exit 1
    fi
else
    print_status "No frontend directory found, skipping build"
fi

# Step 2: Clean up old installation on remote
# print_status "Cleaning up old installation on ${HA_HOST}..."
# ssh -o IgnoreUnknown=UseKeychain "${REMOTE_USER}@${HA_HOST}" "
#     if [ -d '${REMOTE_PATH}' ]; then
#         echo 'Removing old ${REMOTE_PATH}'
#         rm -rf '${REMOTE_PATH}'
#     fi
#     mkdir -p '${REMOTE_PATH}'
# "

# Step 3: Sync files to Home Assistant
print_status "Syncing files to ${HA_HOST}:${REMOTE_PATH}..."

# Change back to workspace directory to ensure correct paths
cd "${WORKSPACE_PATH}"

# Build rsync command with proper path handling
RSYNC_EXCLUDES=""

# Add exclude file if it exists (use absolute path)
if [ -f "${WORKSPACE_PATH}/.rsyncignore" ]; then
    RSYNC_EXCLUDES="--exclude-from=${WORKSPACE_PATH}/.rsyncignore"
    print_status "Using exclude file: ${WORKSPACE_PATH}/.rsyncignore"
else
    # Add common excludes as fallback
    RSYNC_EXCLUDES="--exclude=node_modules --exclude=**/.git --exclude=**/__pycache__ --exclude=**/*.pyc --exclude=src/frontend/dist/ --exclude=.vite/"
    print_status "Using default excludes (no .rsyncignore found)"
fi

# Execute rsync with proper paths
rsync -avz \
    -e "ssh -o IgnoreUnknown=UseKeychain" \
    ${RSYNC_EXCLUDES} \
    --delete \
    "${LOCAL_PATH}/" "${REMOTE_USER}@${HA_HOST}:${REMOTE_PATH}/"

print_success "Files synced successfully"

# Step 4: Verify important files were copied
print_status "Verifying deployment on ${HA_HOST}..."
ssh -o IgnoreUnknown=UseKeychain "${REMOTE_USER}@${HA_HOST}" "
    echo 'Checking essential files...'
    echo 'Config file:' && ls -la '${REMOTE_PATH}/config.json' 2>/dev/null || echo 'Missing config.json'
    echo 'Backend app:' && ls -la '${REMOTE_PATH}/src/backend/app.py' 2>/dev/null || echo 'Missing app.py'
    echo 'Frontend dist:' && ls -la '${REMOTE_PATH}/src/backend/dist/' 2>/dev/null || echo 'Missing frontend dist'
    echo 'Dockerfile:' && ls -la '${REMOTE_PATH}/Dockerfile' 2>/dev/null || echo 'Missing Dockerfile'
"

# Step 5: Build Docker image
print_status "Building Docker image on ${HA_HOST}..."
ssh -o IgnoreUnknown=UseKeychain "${REMOTE_USER}@${HA_HOST}" "
    cd '${REMOTE_PATH}'
    
    # Remove any existing containers and images
    echo 'Cleaning up existing Docker resources...'
    docker ps -a | grep '${ADDON_NAME}' | awk '{print \$1}' | xargs -r docker rm -f 2>/dev/null || true
    docker images | grep '${ADDON_NAME}' | awk '{print \$3}' | xargs -r docker rmi -f 2>/dev/null || true
    
    echo 'Building new Docker image...'
    docker build --no-cache . \
        --tag local/aarch64-addon-${ADDON_NAME}:0.1.0 \
        --build-arg BUILD_FROM=ghcr.io/home-assistant/aarch64-base:latest \
        --build-arg TARGETARCH=arm64
"

print_success "Docker image built successfully"

# Step 6: Reload Home Assistant add-ons
print_status "Reloading Home Assistant add-ons..."
ssh -o IgnoreUnknown=UseKeychain "${REMOTE_USER}@${HA_HOST}" "
    ha addons reload
    sleep 2
    echo 'Available add-ons:'
    ha addons list | grep -i '${ADDON_NAME}' || echo 'Add-on not yet visible, try refreshing HA UI'
"

print_success "Deployment completed!"
echo -e "${GREEN}🎉 AItomations add-on deployed successfully!${NC}"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "1. Go to Home Assistant → Settings → Add-ons"
echo "2. Look for 'AItomations Creator' under Local add-ons"
echo "3. Install and configure with your Gemini API key"
echo "4. Start the add-on and open the Web UI"