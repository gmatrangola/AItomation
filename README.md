# **AItomations - Home Assistant LLM Automation Creator**

A Home Assistant add-on that allows you to create automations by describing what you want in plain English. It uses a Large Language Model (LLM) like Google's Gemini or a local Ollama instance to generate the automation's YAML configuration.

This is the source code for my Home Assistant Addon. The backend for interfacing with the Home Assistant API and the Large Language Models which is written in Python. There is a front-end for the web-interface written Vue 3 + Vuetify + TypeScript. It contains a deployment script that builds both sides, packages up the artifacts and uses rsync to send them to my Test Home Assistant Instance. On my Test Home Assistant instance, I have several entities configured that I can use to test. I set up the addon through Home Assistant's user interface

## **Table of Contents**

* [Features](https://www.google.com/search?q=%23features)  
* [Prerequisites](https://www.google.com/search?q=%23prerequisites)  
* [Development Setup](https://www.google.com/search?q=%23development-setup)  
* [Running in Development Mode](https://www.google.com/search?q=%23running-in-development-mode)  
  * [1. Run the Backend (Python)](https://www.google.com/search?q=%231-run-the-backend-python)  
  * [2. Run the Frontend (Vue)](https://www.google.com/search?q=%232-run-the-frontend-vue)  
  * [3. Access the App](https://www.google.com/search?q=%233-access-the-app)  
* [Debugging in VS Code](https://www.google.com/search?q=%23debugging-in-vs-code)  
  * [1. Create a launch.json File](https://www.google.com/search?q=%231-create-a-launchjson-file)  
  * [2. Start a Debug Session](https://www.google.com/search?q=%232-start-a-debug-session)  
* [Testing in Home Assistant](https://www.google.com/search?q=%23testing-in-home-assistant)  
  * [1. Access Home Assistant's Filesystem](https://www.google.com/search?q=%231-access-home-assistants-filesystem)  
  * [2. Copy the Add-on](https://www.google.com/search?q=%232-copy-the-add-on)  
  * [3. Install and Configure the Add-on](https://www.google.com/search?q=%233-install-and-configure-the-add-on)  
* [Project Structure](https://www.google.com/search?q=%23project-structure)

## **Features**

* **Natural Language Automation:** Simply describe the automation you want.  
* **LLM Integration:** Supports both cloud-based (Gemini) and local (Ollama) language models.  
* **Context-Aware:** Fetches your Home Assistant entities to provide the LLM with relevant context.  
* **Review and Install:** Review the generated YAML and summary before installing.  
* **Seamless UI:** A clean, modern interface built with Vue 3 and Vuetify that integrates with Home Assistant via Ingress.

## **Prerequisites**

Before you begin, ensure you have the following installed on your system:

1. **Visual Studio Code:** The primary editor for this project.  
2. **Docker Desktop:** Required for running VS Code's Dev Containers feature.  
3. **VS Code Dev Containers Extension:** The extension that makes this whole process seamless.

## **Development Setup**

The project is configured to run inside a self-contained Dev Container, which includes Python, Node.js, and all necessary tools.

1. **Clone the Repository:**  
   git clone [https://github.com/your-username/your-addon-repo.git](https://github.com/your-username/your-addon-repo.git)  
   cd your-addon-repo

2. **Open in Dev Container:**  
   * Open the project folder in VS Code.  
   * A notification will pop up asking if you want to "Reopen in Container". Click it.  
   * VS Code will now build the Docker image and configure the development environment. This may take a few minutes on the first run.

The postCreateCommand in .devcontainer/devcontainer.json will automatically install all Python and Node.js dependencies for you.

To validate your code before committing:

```bash
# Quick validation (uses cache)
make validate

# Force full validation
make validate-force

# Run linter only
make lint

# Fix linting issues automatically
make lint-fix

# Run type checking only
make type-check

# Run all checks
make check
```

## **Running in Development Mode**

To work on the application locally, you need to run the Python backend and the Vue frontend simultaneously in separate terminals.

### **1. Run the Backend (Python)**

The backend is a Flask server that handles API requests.

* Open a new terminal in VS Code (Terminal -> New Terminal).  
* Start the Flask server:  
  python add-on/src/backend/app.py

* The server will start on http://localhost:8099. You will see output indicating that the server is running.

### **2. Run the Frontend (Vue)**

The frontend is a Vue 3 application served by Vite's dev server.

* Open a **second** terminal in VS Code by clicking the + icon in the terminal panel.  
* Navigate to the frontend directory and start the dev server:  
  cd add-on/src/frontend  
  pnpm run dev

* The Vite server will start on http://localhost:5173.

### **3. Access the App**

* Open your web browser and navigate to **http://localhost:5173**.  
* You should see the AItomations UI. The vite.config.ts file is configured to automatically proxy any API calls (e.g., to /api/generate_automation) from the frontend to the backend Flask server running on port 8099.

## **Debugging in VS Code**

You can debug both the Python backend and the Vue frontend simultaneously using VS Code's debugger.

### **1. Create a launch.json File**

First, you need to configure the debugger.

1. Go to the **Run and Debug** panel on the left-hand sidebar (or press Ctrl+Shift+D).  
2. Click the link that says "**create a launch.json file**".  
3. Select **Python** from the first dropdown, and then **Flask** from the second.  
4. VS Code will generate a basic launch.json file. **Replace its entire contents** with the configuration below. This config sets up debugging for both Python/Flask and the JavaScript in your Vue app.

.vscode/launch.json:

{  
    "version": "0.2.0",  
    "configurations": [  
        {  
            "name": "Python: Flask",  
            "type": "debugpy",  
            "request": "launch",  
            "module": "flask",  
            "env": {  
                "FLASK_APP": "add-on/src/backend/app.py",  
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
            "name": "Frontend: Debug in Edge",  
            "type": "msedge",  
            "request": "launch",  
            "url": "http://localhost:5173",  
            "webRoot": "${workspaceFolder}/add-on/src/frontend"  
        },  
        {  
            "name": "Frontend: Debug in Chrome",  
            "type": "chrome",  
            "request": "launch",  
            "url": "http://localhost:5173",  
            "webRoot": "${workspaceFolder}/add-on/src/frontend"  
        }  
    ],  
    "compounds": [  
        {  
            "name": "Debug Backend & Frontend (Edge)",  
            "configurations": ["Python: Flask", "Frontend: Debug in Edge"]  
        },  
        {  
            "name": "Debug Backend & Frontend (Chrome)",  
            "configurations": ["Python: Flask", "Frontend: Debug in Chrome"]  
        }  
    ]  
}

### **2. Start a Debug Session**

**Important:** Do **NOT** start the servers manually in the terminal if you are using this debug method. The debugger will launch them for you.

1. Make sure you have shut down any servers you started manually in your terminals.  
2. Go to the **Run and Debug** panel.  
3. From the dropdown at the top, select one of the compound configurations: **Debug Backend & Frontend (Edge)** or **Debug Backend & Frontend (Chrome)**.  
4. Press the green "Start Debugging" arrow (or F5).

VS Code will now:

* Start the Python Flask server in debug mode.  
* Launch a new browser window attached to the debugger.  
* Start the Vite dev server (you'll see its output in the Debug Console).

You can now set breakpoints in your .py files and your .vue files, and the debugger will pause execution as expected.

## **Testing in Home Assistant**

To test your add-on with the full installation experience, you must run it in a proper **Home Assistant OS** environment. The recommended method for macOS is running HA OS in a virtual machine.

### **1. Set Up a Home Assistant OS Virtual Machine**

The standard `docker` and `docker-compose` methods install **Home Assistant Core**, which does **not** include the Supervisor or the Add-on Store.

*Note: We recommend using UTM instead of VirtualBox because UTM supports both Apple Silicon (M1/M2/M3) and Intel-based Macs, providing a single set of instructions for all developers.*

1.  **Install UTM:** Download and install [UTM](https://mac.getutm.app/), a free virtual machine application for macOS.
2.  **Download Home Assistant OS:** Go to the [official releases page](https://github.com/home-assistant/operating-system/releases) and download the `.qcow2.xz` image for your Mac's architecture. This is a compressed file.
    *   **Apple Silicon (M1/M2/M3):** `haos_generic-aarch64-XX.X.qcow2.xz`
    *   **Intel:** `haos_ova-XX.X.qcow2.xz`
    *   After downloading, decompress the file to get the `.qcow2` disk image. On macOS, you can usually just double-click the `.xz` file in Finder to extract it.
3.  **Create the VM in UTM:**
    *   Open UTM and click **+** to create a new machine.
    *   Select **Virtualize**, then **Linux**.
    *   Click **Browse** next to "Boot ISO Image" and select the `.qcow2` file you just unzipped. Click **Continue**.
    *   Accept the default settings for memory and storage (4GB RAM is a good start).
    *   On the final "Summary" screen, check the box for **"Open VM Settings"** and click **Save**.
4.  **Correct the Drives:**
    *   The VM settings will open automatically. Go to the **Drives** section on the left.
    *   You will see two drives. Select the one that is **NOT** your `haos...qcow2` image (it will likely be named `virtio-drive-0` or similar) and click the **Delete** button.
    *   You should now have only one drive left. Click **Save**.
5.  **Start and Configure:**
    *   Start the VM from the main UTM window.
    *   Wait for it to boot. It can take several minutes. The console will eventually show network information and a welcome banner.
    *   Navigate to `http://homeassistant.local:8123` in your browser to complete the setup. If that doesn't work, use the IP address shown in the UTM console window (e.g., `http://192.168.1.123:8123`).
    *   **Note:** If you already have a Home Assistant instance on your network, you should change the hostname of this new test instance to avoid conflicts. You can do this after setup by going to **Settings > System > Network** and changing the "Hostname". For example, changing it to `ha-dev` will make it accessible at `http://ha-dev.local:8123`.

#### **Expanding the Virtual Disk Size (Optional)**

If you need more than the default 32GB of storage for your test instance, you can expand the virtual disk.

1.  **Shut down the VM** in UTM.
2.  **Right-click** the VM and select **Edit**.
3.  Go to the **Drives** tab.
4.  Select the main `haos...` drive.
5.  Change the **Size (GB)** to a larger value (e.g., 64).
6.  **Save** the settings and restart the VM. Home Assistant OS will automatically resize its data partition on the next boot.

### **2. Add Your Local Add-on Repository**

To get your add-on into your new Home Assistant VM, you need to serve your local files over the network.

1.  **Start a Web Server:** In your VS Code terminal, serve your project directory:
    ```bash
    python3 -m http.server 8080
    ```
2.  **Add Repository to Home Assistant:**
    *   In your Home Assistant UI, go to **Settings > Add-ons > Add-on Store**.
    *   Click the three-dots menu and select **Repositories**.
    *   Enter the following URL and click **Add**: `http://host.docker.internal:8080`
    *   *Note: `host.docker.internal` is a special DNS name that resolves to the host machine (your Mac) from within Docker containers, which is how Home Assistant OS runs its components.*

### **3. Install and Configure the Add-on**

1.  Close the repository dialog. A new "Local add-ons" section will appear in the store.
2.  Find your **AItomations** add-on and click **Install**.
3.  Once installed, go to the **Configuration** tab to set up your API keys.
4.  Go to the **Info** tab, start the add-on, and check the **Log** tab for errors.
5.  Click **Open Web UI** to access your add-on's interface.

## **Project Structure**

.  
├── .devcontainer/     # VS Code Development Container configuration  
├── add-on/            # The Home Assistant Add-on itself  
│   ├── Dockerfile     # The production Dockerfile for the add-on  
│   ├── config.json    # Add-on manifest and configuration  
│   ├── run.sh         # Script that runs when the add-on starts  
│   └── src/           # Source code for the frontend and backend  
│       ├── backend/   # Python Flask server  
│       └── frontend/  # Vue 3 + Vuetify user interface  
└── requirements.txt   # Python dependencies  


# Run in the Home Assistant Test Container

The Test container runs on docker on the development box (laptop)

```bash
docker config up -d
```

Shutdown:

```bash
docker config down
```

Connect with
```
"$BROWSER" http://localhost:8123
```

User admin
Pasword: `Adminpassword-123`