# **AItomations \- Home Assistant LLM Automation Creator**

A Home Assistant add-on that allows you to create automations by describing what you want in plain English. It uses a Large Language Model (LLM) like Google's Gemini or a local Ollama instance to generate the automation's YAML configuration.

## **Table of Contents**

* [Features](https://www.google.com/search?q=%23features)  
* [Prerequisites](https://www.google.com/search?q=%23prerequisites)  
* [Development Setup](https://www.google.com/search?q=%23development-setup)  
* [Running in Development Mode](https://www.google.com/search?q=%23running-in-development-mode)  
  * [1\. Run the Backend (Python)](https://www.google.com/search?q=%231-run-the-backend-python)  
  * [2\. Run the Frontend (Vue)](https://www.google.com/search?q=%232-run-the-frontend-vue)  
  * [3\. Access the App](https://www.google.com/search?q=%233-access-the-app)  
* [Debugging in VS Code](https://www.google.com/search?q=%23debugging-in-vs-code)  
  * [1\. Create a launch.json File](https://www.google.com/search?q=%231-create-a-launchjson-file)  
  * [2\. Start a Debug Session](https://www.google.com/search?q=%232-start-a-debug-session)  
* [Testing in Home Assistant](https://www.google.com/search?q=%23testing-in-home-assistant)  
  * [1\. Access Home Assistant's Filesystem](https://www.google.com/search?q=%231-access-home-assistants-filesystem)  
  * [2\. Copy the Add-on](https://www.google.com/search?q=%232-copy-the-add-on)  
  * [3\. Install and Configure the Add-on](https://www.google.com/search?q=%233-install-and-configure-the-add-on)  
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
   git clone \[https://github.com/your-username/your-addon-repo.git\](https://github.com/your-username/your-addon-repo.git)  
   cd your-addon-repo

2. **Open in Dev Container:**  
   * Open the project folder in VS Code.  
   * A notification will pop up asking if you want to "Reopen in Container". Click it.  
   * VS Code will now build the Docker image and configure the development environment. This may take a few minutes on the first run.

The postCreateCommand in .devcontainer/devcontainer.json will automatically install all Python and Node.js dependencies for you.

## **Running in Development Mode**

To work on the application locally, you need to run the Python backend and the Vue frontend simultaneously in separate terminals.

### **1\. Run the Backend (Python)**

The backend is a Flask server that handles API requests.

* Open a new terminal in VS Code (Terminal \-\> New Terminal).  
* Start the Flask server:  
  python add-on/src/backend/app.py

* The server will start on http://localhost:8099. You will see output indicating that the server is running.

### **2\. Run the Frontend (Vue)**

The frontend is a Vue 3 application served by Vite's dev server.

* Open a **second** terminal in VS Code by clicking the \+ icon in the terminal panel.  
* Navigate to the frontend directory and start the dev server:  
  cd add-on/src/frontend  
  pnpm run dev

* The Vite server will start on http://localhost:5173.

### **3\. Access the App**

* Open your web browser and navigate to **http://localhost:5173**.  
* You should see the AItomations UI. The vite.config.ts file is configured to automatically proxy any API calls (e.g., to /api/generate\_automation) from the frontend to the backend Flask server running on port 8099\.

## **Debugging in VS Code**

You can debug both the Python backend and the Vue frontend simultaneously using VS Code's debugger.

### **1\. Create a launch.json File**

First, you need to configure the debugger.

1. Go to the **Run and Debug** panel on the left-hand sidebar (or press Ctrl+Shift+D).  
2. Click the link that says "**create a launch.json file**".  
3. Select **Python** from the first dropdown, and then **Flask** from the second.  
4. VS Code will generate a basic launch.json file. **Replace its entire contents** with the configuration below. This config sets up debugging for both Python/Flask and the JavaScript in your Vue app.

.vscode/launch.json:

{  
    "version": "0.2.0",  
    "configurations": \[  
        {  
            "name": "Python: Flask",  
            "type": "debugpy",  
            "request": "launch",  
            "module": "flask",  
            "env": {  
                "FLASK\_APP": "add-on/src/backend/app.py",  
                "FLASK\_DEBUG": "1"  
            },  
            "args": \[  
                "run",  
                "--no-debugger",  
                "--no-reload",  
                "--port=8099"  
            \],  
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
    \],  
    "compounds": \[  
        {  
            "name": "Debug Backend & Frontend (Edge)",  
            "configurations": \["Python: Flask", "Frontend: Debug in Edge"\]  
        },  
        {  
            "name": "Debug Backend & Frontend (Chrome)",  
            "configurations": \["Python: Flask", "Frontend: Debug in Chrome"\]  
        }  
    \]  
}

### **2\. Start a Debug Session**

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

To see your add-on working in a real Home Assistant environment:

### **1\. Access Home Assistant's Filesystem**

You need a way to copy your add-on files into your Home Assistant instance. The easiest method is to install the **Samba share** add-on or the **Visual Studio Code** add-on from the official add-on store, which give you access to the HA configuration folders.

### **2\. Copy the Add-on**

1. Connect to your Home Assistant filesystem (e.g., via Samba).  
2. Navigate to the root directory where you see config, ssl, share, etc.  
3. Find the addons directory. If it doesn't exist, create it.  
4. Copy your local **add-on** folder (the one containing config.json, run.sh, etc.) into the /addons directory.

The final path inside Home Assistant should be /addons/add-on.

### **3\. Install and Configure the Add-on**

1. In Home Assistant, go to **Settings \-\> Add-ons \-\> Add-on Store**.  
2. Click the three-dots menu at the top right and select **Check for updates**.  
3. After a few moments, a new section called "Local add-ons" should appear, containing your **AItomations** add-on.  
4. Click on the add-on and click **Install**.  
5. Once installed, go to the **Configuration** tab and enter your LLM provider details (e.g., your Gemini API Key or the URL for your Ollama instance). Click **Save**.  
6. Go back to the **Info** tab, start the add-on, and check the **Log** tab to ensure there are no errors.  
7. If the add-on starts successfully, you can click **Open Web UI** to access the interface through Ingress.

## **Project Structure**

.  
├── .devcontainer/     \# VS Code Development Container configuration  
├── add-on/            \# The Home Assistant Add-on itself  
│   ├── Dockerfile     \# The production Dockerfile for the add-on  
│   ├── config.json    \# Add-on manifest and configuration  
│   ├── run.sh         \# Script that runs when the add-on starts  
│   └── src/           \# Source code for the frontend and backend  
│       ├── backend/   \# Python Flask server  
│       └── frontend/  \# Vue 3 \+ Vuetify user interface  
└── requirements.txt   \# Python dependencies  
