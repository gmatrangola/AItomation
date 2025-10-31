# AItomations - Home Assistant Automation Creator

Create Home Assistant automations using natural language! Describe what you want in plain English, and AItomations uses AI (Google Gemini or local Ollama) to generate the YAML configuration for you.

This is the repository for the source code for the AITomations Home Assistant Add On. If you are looking to install and use the add on please go to [The installation repo](https://github.com/gmatrangola/aitomation-install)

The following information is for my reference and future contributors to the project. It might also serve as an example for efficently building Home Assistant Add Ons with a user interface and back end.

![Version](https://img.shields.io/badge/version-1.0.0-blue)
![License](https://img.shields.io/badge/license-MIT-green)

## ✨ Features

* **Natural Language Automation** - Just describe what you want in plain English
* **Multiple LLM Providers** - Use Google Gemini (cloud) or Ollama (local)
* **Context-Aware** - Automatically fetches your Home Assistant entities for accurate suggestions
* **Conversational Interface** - Chat with the AI to refine your automation
* **Real-time Streaming** - See the AI's response as it's generated
* **Review Before Install** - Preview the YAML and explanation before installing
* **Modern UI** - Clean interface built with Vue 3 and Vuetify

## 📋 Table of Contents

* [Prerequisites](#prerequisites)
* [Development Setup](#development-setup)
* [Running in Development Mode](#running-in-development-mode)
* [Debugging in VS Code](#debugging-in-vs-code)
* [Testing in Home Assistant](#testing-in-home-assistant)
* [Building and Deploying](#building-and-deploying)
* [Project Structure](#project-structure)
* [Contributing](#contributing)
* [License](#license)

## 🔧 Prerequisites

Before you begin, ensure you have:

1. **Visual Studio Code** - The primary editor for this project
2. **Docker Desktop** - Required for VS Code Dev Containers
3. **VS Code Dev Containers Extension** - For the development environment

## 🚀 Development Setup

This project uses VS Code Dev Containers for a consistent development environment with all tools pre-installed.

### 1. Clone and Open

```bash
git clone https://github.com/gmatrangola/aitomations.git
cd aitomations
```

Open the folder in VS Code. When prompted, click **"Reopen in Container"**. The first build may take a few minutes.

### 2. Validate Your Setup

The dev container automatically installs all dependencies. To validate everything is working:

```bash
# Quick validation (uses cache)
make validate

# Force full validation
make validate-force

# Run linter only
make lint

# Fix linting issues
make lint-fix

# Run type checking
make type-check
```

## 💻 Running in Development Mode

Run the backend and frontend simultaneously in separate terminals.

### Backend (Python/Flask)

```bash
python aitomations/src/backend/app.py
```

The server starts at `http://localhost:8099`

### Frontend (Vue/Vite)

```bash
cd aitomations/src/frontend
pnpm run dev
```

The dev server starts at `http://localhost:5173`

### Access the App

Open `http://localhost:5173` in your browser. The Vite dev server automatically proxies API calls to the backend.

## 🐛 Debugging in VS Code

Debug both backend and frontend simultaneously with full breakpoint support.

### Setup Debug Configuration

Create `.vscode/launch.json`:

```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Python: Flask",
            "type": "debugpy",
            "request": "launch",
            "module": "flask",
            "env": {
                "FLASK_APP": "aitomations/src/backend/app.py",
                "FLASK_DEBUG": "1"
            },
            "args": [
                "run",
                "--no-debugger",
                "--no-reload",
                "--port=8099"
            ],
            "jinja": true,
            "justMyCode": true
        },
        {
            "name": "Frontend: Chrome",
            "type": "chrome",
            "request": "launch",
            "url": "http://localhost:5173",
            "webRoot": "${workspaceFolder}/aitomations/src/frontend"
        }
    ],
    "compounds": [
        {
            "name": "Full Stack Debug",
            "configurations": ["Python: Flask", "Frontend: Chrome"]
        }
    ]
}
```

### Start Debugging

1. Stop any manually started servers
2. Open **Run and Debug** panel (Ctrl+Shift+D)
3. Select **"Full Stack Debug"** from the dropdown
4. Press F5 or click the green play button

Set breakpoints in `.py` and `.vue` files - the debugger will pause execution as expected.

## 🏠 Testing in Home Assistant

Test the add-on in a complete Home Assistant OS environment using a virtual machine.

### Method 1: UTM (Recommended for macOS)

UTM supports both Apple Silicon and Intel Macs with a single setup process.

#### Install Home Assistant OS

1. **Install UTM**: Download from [mac.getutm.app](https://mac.getutm.app/)

2. **Download HA OS**: Get the appropriate image from the [releases page](https://github.com/home-assistant/operating-system/releases):
   - Apple Silicon: `haos_generic-aarch64-XX.X.qcow2.xz`
   - Intel: `haos_ova-XX.X.qcow2.xz`
   - Extract the `.xz` file (double-click in Finder)

3. **Create VM**:
   - Open UTM → Click **+** → **Virtualize** → **Linux**
   - Select the `.qcow2` file as boot image
   - Accept defaults (4GB RAM recommended)
   - Check **"Open VM Settings"** → **Save**

4. **Fix Drives**:
   - Go to **Drives** section
   - Delete the drive that is NOT your `haos...qcow2` image
   - **Save**

5. **Start and Configure**:
   - Start the VM
   - Wait for boot (several minutes)
   - Access at `http://homeassistant.local:8123` or use the IP shown in console
   - Complete the onboarding wizard

**Tip**: Change hostname to avoid conflicts with existing HA instances:
**Settings** → **System** → **Network** → Change "Hostname" to `ha-dev`

#### Load Your Add-on

1. **Build the add-on**:
   ```bash
   make build
   ```

2. **Start local web server**:
   ```bash
   python3 -m http.server 8080
   ```

3. **Add repository in Home Assistant**:
   - **Settings** → **Add-ons** → **Add-on Store**
   - Three-dots menu → **Repositories**
   - Add: `http://host.docker.internal:8080`

4. **Install**:
   - Find **AItomations Creator** in "Local add-ons"
   - Click **Install**
   - Configure your API keys
   - Start the add-on
   - Click **Open Web UI**

### Method 2: Docker Test Container (Quick Testing)

For quick testing without full HA OS features:

```bash
# Start test container
docker-compose up -d

# Access Home Assistant
# http://localhost:8123
# User: admin
# Password: Adminpassword-123

# Shutdown
docker-compose down
```

**Note**: This runs Home Assistant Core, which lacks the Supervisor and Add-on Store.

## 📦 Building and Deploying

### Build for Release

```bash
# Full build with validation
make build

# Quick build (skip type checking)
make build-incremental

# Frontend only
make build-frontend
```

### Deploy to Test Instance

Configure deployment in `.deploy.test.env`:

```bash
HA_HOST=192.168.1.100
HA_USER=root
HA_PORT=22
HA_PATH=/addons/local_aitomations-creator
```

Deploy:

```bash
# Build and deploy
make deploy TARGET=test

# Deploy without rebuilding
make deploy-quick TARGET=test

# Restart add-on
make restart TARGET=test

# View logs
make logs TARGET=test
```

## 📁 Project Structure

```
.
├── .devcontainer/              # VS Code Dev Container config
├── aitomations/                # Main add-on directory
│   ├── src/
│   │   ├── backend/           # Python Flask API
│   │   │   ├── app.py        # Main Flask application
│   │   │   ├── api/          # API routes and errors
│   │   │   └── llm/          # LLM provider implementations
│   │   └── frontend/         # Vue 3 + Vuetify UI
│   │       ├── src/
│   │       │   ├── components/  # Vue components
│   │       │   ├── views/       # Page views
│   │       │   ├── services/    # API and error services
│   │       │   └── composables/ # Vue composables
│   ├── Dockerfile            # Production container
│   ├── config.json          # Add-on manifest
│   └── run.sh              # Add-on startup script
├── build/                   # Build output (git-ignored)
├── Makefile                # Build and deployment commands
└── README.md
```

## 🤝 Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](aitomations/Contributions.md) for guidelines.

### Quick Start for Contributors

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Make your changes
4. Validate: `make validate`
5. Commit: `git commit -m 'Add amazing feature'`
6. Push: `git push origin feature/amazing-feature`
7. Open a Pull Request

### Code Standards

- **Python**: Follow PEP 8, use `ruff` for linting
- **TypeScript/Vue**: Follow the ESLint configuration
- **All code must pass**: `make validate` before committing

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 📫 Support

- **Issues**: [GitHub Issues](https://github.com/gmatrangola/aitomations/issues)
- **Discussions**: [GitHub Discussions](https://github.com/gmatrangola/aitomations/discussions)
- **Home Assistant Community**: [Community Forum](https://community.home-assistant.io/)

---

Made with ❤️ for the Home Assistant community