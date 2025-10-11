.PHONY: help install build clean deploy deploy-prod deploy-test test lint format validate validate-force

# Default target
.DEFAULT_GOAL := help

# Use bash for all commands
SHELL := /bin/bash

# Configuration
FRONTEND_DIR := aitomations/src/frontend
BACKEND_DIR := aitomations/src/backend
BUILD_DIR := build
ADDON_DIR := aitomations
SCRIPTS_DIR := scripts
ADDON_SLUG := aitomations-creator
ADDON_FULL_SLUG := local_$(ADDON_SLUG)
CACHE_DIR := .make-cache

# Deployment targets (loaded from .env or defaults)
TARGET ?= test
include .deploy.env
-include .deploy.$(TARGET).env

# Find all source files for dependency tracking
FRONTEND_SRC := $(shell find $(FRONTEND_DIR)/src -type f \( -name "*.vue" -o -name "*.ts" -o -name "*.js" \) 2>/dev/null)
BACKEND_SRC := $(shell find $(BACKEND_DIR) -type f -name "*.py" 2>/dev/null)

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-20s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

# Create cache directory
$(CACHE_DIR):
	@mkdir -p $(CACHE_DIR)

install: ## Install all dependencies
	@echo "Installing frontend dependencies..."
	cd $(FRONTEND_DIR) && pnpm install
	@echo "Installing backend dependencies..."
	pip3 install --user -r $(ADDON_DIR)/requirements.txt
	pip3 install --user pytest pytest-cov ruff black
	@echo "✓ All dependencies installed"

install-frontend: ## Install frontend dependencies only
	cd $(FRONTEND_DIR) && pnpm install

install-backend: ## Install backend dependencies only
	pip3 install --user -r $(ADDON_DIR)/requirements.txt
	pip3 install --user pytest pytest-cov ruff black

# Backend validation with caching
$(CACHE_DIR)/backend-validated: $(BACKEND_SRC) | $(CACHE_DIR)
	@echo "Backend files changed, validating..."
	@python3 $(SCRIPTS_DIR)/validate_backend.py
	@touch $(CACHE_DIR)/backend-validated

validate-backend: $(CACHE_DIR)/backend-validated ## Validate Python syntax and imports (cached)

validate-backend-force: ## Force backend validation (ignore cache)
	@rm -f $(CACHE_DIR)/backend-validated
	@$(MAKE) validate-backend

# Frontend validation with caching
$(CACHE_DIR)/frontend-validated: $(FRONTEND_SRC) $(FRONTEND_DIR)/tsconfig.json | $(CACHE_DIR)
	@echo "Frontend files changed, validating..."
	@cd $(FRONTEND_DIR) && pnpm run type-check 2>/dev/null || \
	 (echo "TypeScript validation..." && npx vue-tsc --noEmit || true)
	@touch $(CACHE_DIR)/frontend-validated

validate-frontend: $(CACHE_DIR)/frontend-validated ## Validate TypeScript/Vue syntax (cached)

validate-frontend-force: ## Force frontend validation (ignore cache)
	@rm -f $(CACHE_DIR)/frontend-validated
	@$(MAKE) validate-frontend

validate: validate-backend validate-frontend ## Validate all code (cached)

validate-force: validate-backend-force validate-frontend-force ## Force validation of all code (ignore cache)

build: clean validate ## Build frontend and package add-on
	@echo "Building frontend..."
	cd $(FRONTEND_DIR) && pnpm run build
	@echo "✓ Frontend built"
	@echo ""
	@echo "Packaging add-on..."
	@mkdir -p $(BUILD_DIR)
	@rsync -a \
	    --exclude='node_modules' \
	    --exclude='.git' \
	    --exclude='dist' \
	    --exclude='*.pyc' \
	    --exclude='__pycache__' \
	    --exclude='.DS_Store' \
	    --exclude='*.egg-info' \
	    --exclude='.pytest_cache' \
	    --exclude='.ruff_cache' \
	    $(ADDON_DIR)/ $(BUILD_DIR)/
	@rsync -a $(FRONTEND_DIR)/dist/ $(BUILD_DIR)/src/frontend/dist/
	@echo "✓ Add-on packaged to $(BUILD_DIR)/"

build-frontend: ## Build frontend only
	cd $(FRONTEND_DIR) && pnpm run build

build-backend: validate-backend ## Build/validate backend only
	@echo "✓ Backend validated"

clean: ## Clean build artifacts
	@echo "Cleaning build artifacts..."
	@rm -rf $(BUILD_DIR)
	@rm -rf $(FRONTEND_DIR)/dist
	@rm -rf $(FRONTEND_DIR)/node_modules/.vite
	@find . -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name '*.egg-info' -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name '.pytest_cache' -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name '.ruff_cache' -exec rm -rf {} + 2>/dev/null || true
	@echo "✓ Cleaned"

clean-all: clean ## Clean build artifacts and validation cache
	@echo "Cleaning validation cache..."
	@rm -rf $(CACHE_DIR)
	@echo "✓ All cleaned"

test: ## Run all tests
	@echo "Running frontend tests..."
	cd $(FRONTEND_DIR) && pnpm run test || true
	@echo ""
	@echo "Running backend tests..."
	cd $(BACKEND_DIR) && python3 -m pytest || true

test-frontend: ## Run frontend tests only
	cd $(FRONTEND_DIR) && pnpm run test

test-backend: ## Run backend tests only
	cd $(BACKEND_DIR) && python3 -m pytest

lint: ## Run linters
	@echo "Linting frontend..."
	cd $(FRONTEND_DIR) && pnpm run lint || true
	@echo ""
	@echo "Linting backend..."
	cd $(BACKEND_DIR) && ruff check . || true

lint-fix: ## Fix linting issues
	cd $(FRONTEND_DIR) && pnpm run lint:fix
	cd $(BACKEND_DIR) && ruff check --fix .

format: ## Format code
	@echo "Formatting frontend..."
	cd $(FRONTEND_DIR) && pnpm run format || true
	@echo ""
	@echo "Formatting backend..."
	cd $(BACKEND_DIR) && ruff format . || true

dev-frontend: ## Run frontend dev server
	cd $(FRONTEND_DIR) && pnpm run dev

dev-backend: ## Run backend dev server
	cd $(BACKEND_DIR) && python3 app.py

watch: ## Watch and rebuild on changes
	cd $(FRONTEND_DIR) && pnpm run build -- --watch

deploy: build ## Deploy to target (default: test). Usage: make deploy TARGET=prod
	@echo "Deploying to $(TARGET)..."
	@if [ -z "$(HA_HOST)" ]; then \
	    echo "Error: HA_HOST not set for target $(TARGET)"; \
	    echo "Create .deploy.$(TARGET).env with HA_HOST, HA_USER, etc."; \
	    exit 1; \
	fi
	@if [ "$(TARGET)" = "prod" ]; then \
	    echo "⚠ WARNING: Deploying to PRODUCTION!"; \
	    echo "Continue? [y/N] "; \
	    read REPLY; \
	    if [ "$$REPLY" != "y" ] && [ "$$REPLY" != "Y" ]; then \
	        echo "Deployment cancelled"; \
	        exit 1; \
	    fi; \
	fi
	@echo "Testing SSH connection..."
	@ssh -p $(HA_PORT) -o ConnectTimeout=5 $(HA_USER)@$(HA_HOST) "echo 'Connected'" || \
	    (echo "SSH connection failed"; exit 1)
	@echo "Creating remote directory..."
	@ssh -p $(HA_PORT) $(HA_USER)@$(HA_HOST) "mkdir -p $(HA_PATH)"
	@echo "Syncing files..."
	@rsync -avz --delete --progress \
	    -e "ssh -p $(HA_PORT)" \
	    $(BUILD_DIR)/ \
	    $(HA_USER)@$(HA_HOST):$(HA_PATH)/
	@echo "✓ Deployed to $(TARGET)"
	@echo ""
	@echo "Next steps:"
	@echo "  1. Settings > Add-ons > Check for updates or reload"
	@echo "  2. Restart the AItomations add-on"
	@echo "  3. Hard refresh browser (Ctrl+Shift+R or Cmd+Shift+R)"

deploy-test: ## Deploy to test instance
	@$(MAKE) deploy TARGET=test

deploy-prod: ## Deploy to production instance
	@$(MAKE) deploy TARGET=prod

deploy-quick: ## Quick deploy without rebuild (use existing build)
	@echo "Deploying without rebuild..."
	@if [ ! -d "$(BUILD_DIR)" ]; then \
	    echo "Error: Build directory doesn't exist. Run 'make build' first."; \
	    exit 1; \
	fi
	@echo "Testing SSH connection..."
	@ssh -p $(HA_PORT) -o ConnectTimeout=5 $(HA_USER)@$(HA_HOST) "echo 'Connected'" || \
	    (echo "SSH connection failed"; exit 1)
	@echo "Syncing files..."
	@rsync -avz --delete --progress \
	    -e "ssh -p $(HA_PORT)" \
	    $(BUILD_DIR)/ \
	    $(HA_USER)@$(HA_HOST):$(HA_PATH)/
	@echo "✓ Deployed to $(TARGET)"

ssh: ## SSH into target instance
	@ssh -p $(HA_PORT) $(HA_USER)@$(HA_HOST)

logs: ## Tail add-on logs on target instance
	@echo "Tailing logs for $(ADDON_FULL_SLUG) add-on..."
	@ssh -p $(HA_PORT) $(HA_USER)@$(HA_HOST) \
	    "docker logs -f addon_$(ADDON_FULL_SLUG) 2>&1 || \
	     ha addons logs $(ADDON_FULL_SLUG) -f"

restart: ## Restart add-on on target instance
	@echo "Restarting $(ADDON_FULL_SLUG) add-on..."
	@ssh -p $(HA_PORT) $(HA_USER)@$(HA_HOST) \
	    "docker restart addon_$(ADDON_FULL_SLUG) 2>/dev/null || \
	     ha addons restart $(ADDON_FULL_SLUG)"
	@echo "✓ Add-on restart command sent"
	@echo "Wait a few seconds, then check: make status TARGET=$(TARGET)"

status: ## Check add-on status on target instance
	@ssh -p $(HA_PORT) $(HA_USER)@$(HA_HOST) \
	    "docker ps --filter name=addon_$(ADDON_FULL_SLUG) --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}' || \
	     ha addons info $(ADDON_FULL_SLUG)"

info: ## Show deployment target info
	@echo "Target:     $(TARGET)"
	@echo "Host:       $(HA_HOST)"
	@echo "User:       $(HA_USER)"
	@echo "Port:       $(HA_PORT)"
	@echo "Path:       $(HA_PATH)"
	@echo "Slug:       $(ADDON_SLUG)"
	@echo "Full Slug:  $(ADDON_FULL_SLUG)"

version: ## Show version info
	@echo "Frontend:"
	@cd $(FRONTEND_DIR) && pnpm --version && node --version
	@echo ""
	@echo "Backend:"
	@python3 --version
	@pip3 --version

# New helper target for full deploy cycle
deploy-full: deploy restart ## Deploy and restart in one command
	@echo ""
	@echo "Waiting for add-on to start..."
	@sleep 5
	@$(MAKE) status TARGET=$(TARGET)
	@echo ""
	@echo "✓ Deployment complete!"
	@echo "Remember to hard refresh your browser!"

# Verify deployment
verify: ## Verify deployment files on target
	@echo "Checking deployment at $(HA_PATH)..."
	@ssh -p $(HA_PORT) $(HA_USER)@$(HA_HOST) \
	    "ls -lah $(HA_PATH) && \
	     echo '' && \
	     echo 'Frontend dist:' && \
	     ls -lah $(HA_PATH)/src/frontend/dist/ 2>/dev/null || echo 'Not found'"