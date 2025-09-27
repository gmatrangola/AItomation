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

# Development mode flag
DEVELOPMENT=${DEVELOPMENT:-false}
SKIP_FRONTEND=${SKIP_FRONTEND:-false}
SKIP_DOCKER=${SKIP_DOCKER:-false}

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

# Function to check if frontend needs building
frontend_needs_build() {
    local frontend_dir="${LOCAL_PATH}/src/frontend"
    local dist_dir="${LOCAL_PATH}/src/backend/dist"
    
    # If SKIP_FRONTEND is set, never build
    if [ "$SKIP_FRONTEND" = "true" ]; then
        return 1
    fi
    
    # If dist doesn't exist, we need to build
    if [ ! -d "$dist_dir" ]; then
        return 0
    fi
    
    # Check if any frontend source files are newer than the dist directory
    if [ -n "$(find "$frontend_dir/src" -newer "$dist_dir" 2>/dev/null)" ]; then
        return 0
    fi
    
    # Check if package files changed
    if [ "$frontend_dir/package.json" -nt "$dist_dir" ] || [ "$frontend_dir/pnpm-lock.yaml" -nt "$dist_dir" ]; then
        return 0
    fi
    
    return 1
}

# Function to check if Docker needs rebuilding
docker_needs_rebuild() {
    # If SKIP_DOCKER is set, never rebuild
    if [ "$SKIP_DOCKER" = "true" ]; then
        return 1
    fi
    
    # Check if Docker-related files changed
    local docker_files=(
        "${LOCAL_PATH}/Dockerfile"
        "${LOCAL_PATH}/requirements.txt"
        "${LOCAL_PATH}/run.sh"
        "${LOCAL_PATH}/config.json"
    )
    
    local backend_dir="${LOCAL_PATH}/src/backend"
    
    # Get last image build time
    local last_build=$(ssh -o IgnoreUnknown=UseKeychain "${REMOTE_USER}@${HA_HOST}" \
        "docker images --format '{{.CreatedAt}}' local/aarch64-addon-${ADDON_NAME}:0.1.0 2>/dev/null | head -1")
    
    if [ -z "$last_build" ]; then
        return 0  # No image exists, need to build
    fi
    
    # Convert to timestamp (this is approximate)
    local build_timestamp=$(date -j -f "%Y-%m-%d %H:%M:%S" "$last_build" "+%s" 2>/dev/null || echo "0")
    
    # Check if any critical files are newer
    for file in "${docker_files[@]}"; do
        if [ "$file" -nt "$build_timestamp" ]; then
            return 0
        fi
    done
    
    # Check if backend files changed
    if [ -n "$(find "$backend_dir" -newer "$build_timestamp" 2>/dev/null)" ]; then
        return 0
    fi
    
    return 1
}

# Step 1: Build frontend and copy to backend
if [ -d "${LOCAL_PATH}/src/frontend" ]; then
    if frontend_needs_build; then
        print_status "Frontend files changed, building..."
        cd "${LOCAL_PATH}/src/frontend"
        
        if [ ! -d "node_modules" ]; then
            print_status "Installing frontend dependencies..."
            pnpm install
        fi
        
        if [ "$DEVELOPMENT" = "true" ]; then
            print_status "Development build (faster)..."
            pnpm run build:dev
        else
            print_status "Production build..."
            pnpm run build
        fi
        
        print_status "Copying built frontend to backend..."
        mkdir -p "${LOCAL_PATH}/src/backend/dist"
        cp -r dist/* "${LOCAL_PATH}/src/backend/dist/"
        print_success "Frontend built and copied successfully"
    else
        print_success "Frontend unchanged, skipping build"
    fi
else
    print_status "No frontend directory found, skipping build"
fi

# Step 2: Sync files to Home Assistant
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

# Step 3: Verify important files were copied
print_status "Verifying deployment on ${HA_HOST}..."
ssh -o IgnoreUnknown=UseKeychain "${REMOTE_USER}@${HA_HOST}" "
    echo 'Checking essential files...'
    echo 'Config file:' && ls -la '${REMOTE_PATH}/config.json' 2>/dev/null || echo 'Missing config.json'
    echo 'Backend app:' && ls -la '${REMOTE_PATH}/src/backend/app.py' 2>/dev/null || echo 'Missing app.py'
    echo 'Frontend dist:' && ls -la '${REMOTE_PATH}/src/backend/dist/' 2>/dev/null || echo 'Missing frontend dist'
    echo 'Dockerfile:' && ls -la '${REMOTE_PATH}/Dockerfile' 2>/dev/null || echo 'Missing Dockerfile'
"

# Step 4: Build Docker image (if needed)
if docker_needs_rebuild; then
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
else
    print_success "Docker image unchanged, skipping rebuild"
fi

# Step 5: Reload Home Assistant add-ons
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

# Show deployment summary
echo ""
echo -e "${YELLOW}Deployment Summary:${NC}"
echo "- Frontend build: $([ "$SKIP_FRONTEND" = "true" ] && echo "Skipped" || echo "$(frontend_needs_build && echo "Built" || echo "Cached")")"
echo "- Docker image: $([ "$SKIP_DOCKER" = "true" ] && echo "Skipped" || echo "$(docker_needs_rebuild && echo "Rebuilt" || echo "Cached")")"
echo "- Mode: $([ "$DEVELOPMENT" = "true" ] && echo "Development" || echo "Production")"