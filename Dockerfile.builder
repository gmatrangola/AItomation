# This Dockerfile creates a base image with all node_modules pre-installed.
# You only need to build and push this when your dependencies change.
FROM node:20-alpine

WORKDIR /usr/src/app

# Install pnpm globally
RUN npm install -g pnpm

# Copy only the dependency definition files
COPY add-on/src/frontend/package.json add-on/src/frontend/pnpm-lock.yaml* ./

# Install dependencies. This is the slow step we are pre-caching.
RUN pnpm install --frozen-lockfile --reporter=append-only

# The final image will just contain the installed node_modules.
# The source code is not needed here.