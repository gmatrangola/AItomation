# AItomations - Home Assistant LLM Automation Creator Instructions

This document provides guidance for AI coding agents working on the AItomations codebase.

## Project Overview & Architecture

AItomations is a Home Assistant Add-on with a decoupled frontend and backend, running inside a single Docker container.

-   **Backend**: A Python Flask application located in `aitomations/src/backend/`.
    -   It serves a REST API for the frontend.
    -   It communicates with the Home Assistant Supervisor API to fetch entities and services.
    -   It integrates with Large Language Models (LLMs) like Gemini and Ollama via modules in `aitomations/src/llm/`.
    -   The main application file is `app.py`. API routes are defined in `api/routes.py`.

-   **Frontend**: A Vue 3 + TypeScript + Vuetify Single Page Application (SPA) located in `aitomations/src/frontend/`.
    -   It provides the user interface for creating automations.
    -   It communicates with the Flask backend.
    -   Key components are in `src/components/`, such as `AIChat.vue`.

-   **Home Assistant Integration**:
    -   The add-on is defined by `aitomations/config.json`, which specifies configuration options, ports, and ingress support.
    -   The `run.sh` script is the entrypoint for the add-on's Docker container. It starts the Python backend. In the production container, the frontend is served as static files by the backend.

## Developer Workflow

The primary development environment is the VS Code Dev Container, which provides all necessary dependencies (Python, Node.js, etc.).

### Running in Development

To run the application locally, you need two separate terminals:

1.  **Run the Backend (Flask)**:
    ```bash
    python aitomations/src/backend/app.py
    ```
    The backend runs on `http://localhost:8099`.

2.  **Run the Frontend (Vue)**:
    ```bash
    cd aitomations/src/frontend
    pnpm install # If you haven't already
    pnpm run dev
    ```
    The frontend is available at `http://localhost:5173`. The Vite dev server is configured in `vite.config.ts` to proxy API requests from `/api/*` to the backend at port 8099.

### Debugging

The `README.md` contains a complete `.vscode/launch.json` configuration for compound debugging. Use the **"Debug Backend & Frontend"** launch configuration from the "Run and Debug" panel to start a debug session for both the Python backend and the Vue frontend simultaneously.

### Testing in Home Assistant

The `README.md` provides detailed instructions for setting up a Home Assistant OS VM and deploying the add-on for end-to-end testing. This involves serving the local add-on repository over HTTP and adding it to the Home Assistant Add-on Store.

## Code Conventions

-   **Backend**: The Flask app follows standard Flask patterns. It uses a base `LLM` class in `aitomations/src/llm/base.py` which other LLM providers inherit from.
-   **Frontend**: The Vue app uses the Composition API (`<script setup>`). Composables for shared logic are located in `aitomations/src/frontend/src/composables/`.
