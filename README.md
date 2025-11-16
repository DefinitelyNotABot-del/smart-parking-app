# 🅿️ Smart Parking Management System

**What it does:** Real-time parking spot booking with AI-powered search, interactive maps, and owner dashboards. Customers find and book parking, owners manage lots and view analytics.

---

## ⚡ Super Quick Setup (Copy-Paste)

```bash
git clone https://github.com/DefinitelyNotABot-del/smart-parking-app.git
cd smart-parking-app
python -m venv .venv
# Windows: .venv\Scripts\activate | Linux/Mac: source .venv/bin/activate
pip install -r requirements.txt
python run.py
```
**Open:** http://localhost:5000

---

## 🚀 Detailed Setup Guide

### Prerequisites (Install These First)

1. **Python 3.12+** - [Download here](https://www.python.org/downloads/)
   - ✅ **SQLite3 included** (no separate install needed)
   - During install: ✓ Check "Add Python to PATH"
   - Verify: `python --version`

2. **VS Code** - [Download here](https://code.visualstudio.com/)
   - Install "Python" extension by Microsoft

3. **Git** - [Download here](https://git-scm.com/downloads/)
   - Verify: `git --version`

4. **Docker Desktop** (Optional) - [Download here](https://www.docker.com/products/docker-desktop/)
   - Only needed for containerized deployment
   - Verify: `docker --version`

## 🚀 Setup in VS Code (Recommended)

### Step 1: Clone & Open Project

```bash
git clone https://github.com/DefinitelyNotABot-del/smart-parking-app.git
cd smart-parking-app
code .
```

### Step 2: Select Python Interpreter in VS Code

1. Press `Ctrl+Shift+P` (Windows/Linux) or `Cmd+Shift+P` (Mac)
2. Type: `Python: Select Interpreter`
3. Choose your Python 3.12+ installation

### Step 3: Create Virtual Environment

**In VS Code Terminal** (`` Ctrl+` ``):

**Windows:**
```bash
python -m venv .venv
.venv\Scripts\activate
```

**macOS/Linux:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

You should see `(.venv)` in your terminal prompt.

### Step 4: Install All Dependencies

```bash
pip install -r requirements.txt
```

This installs:
- Flask & Flask-SocketIO (web framework & real-time features)
- Scikit-learn, NumPy, Pandas (ML/AI models)
- Gunicorn, Eventlet (production server)
- All other dependencies automatically

**Note:** SQLite3 is already included with Python - no separate installation needed!

### Step 5: Run the Application

```bash
python run.py
```

**Expected output:**
```
✓ Databases initialized
 * Running on http://127.0.0.1:5000
```

Open in browser: **http://localhost:5000**

### Step 6: Start Coding!

- Press `F5` in VS Code to run with debugger
- Or use terminal: `python run.py`
- Database files auto-created in `instance/` folder
- Hot reload enabled in development mode

## 🐧 Alternative: Command Line Setup (No VS Code)

### Quick Setup

```bash
# 1. Clone repo
git clone https://github.com/DefinitelyNotABot-del/smart-parking-app.git
cd smart-parking-app

# 2. Create & activate virtual environment
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/Mac: source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run app
python run.py
```

Open: **http://localhost:5000**

## 🐳 Docker Setup (Optional)

### Prerequisites
- Docker Desktop installed and running

### Setup Steps

**1. Build Docker Image**
```bash
docker build -t smart-parking-app .
```

**2. Run Container**
```bash
docker run -d -p 5000:5000 --name parking-app smart-parking-app
```

**3. Verify Running**
```bash
docker ps
```

**4. View Logs**
```bash
docker logs parking-app
```

**5. Stop & Remove**
```bash
docker stop parking-app
docker rm parking-app
```

Open: **http://localhost:5000**

## ☁️ Azure Deployment

### Prerequisites

- Azure account with active subscription
- Azure CLI installed
- GitHub repository connected

### Automated Deployment (Recommended)

1. **Configure Azure Resources**

```bash
chmod +x setup-azure.sh
./setup-azure.sh
```

2. **Add GitHub Secrets**

Go to: `Settings` → `Secrets and variables` → `Actions`

Add these secrets (values from setup script output):
- `AZURE_CLIENT_ID`
- `AZURE_TENANT_ID`
- `AZURE_SUBSCRIPTION_ID`
- `FLASK_SECRET_KEY`

3. **Deploy via GitHub Actions**

```bash
git add .
git commit -m "Deploy to Azure"
git push origin main
```

Your app will be deployed automatically via CI/CD pipeline.

### Manual Azure Deployment

```bash
# Login to Azure
az login

# Create resource group
az group create --name smart-parking-rg --location eastus

# Create App Service plan (F1 Free tier)
az appservice plan create --name smart-parking-plan --resource-group smart-parking-rg --sku F1 --is-linux

# Create web app
az webapp create --resource-group smart-parking-rg --plan smart-parking-plan --name smart-parking-app --runtime "PYTHON:3.12"

# Configure startup command
az webapp config set --resource-group smart-parking-rg --name smart-parking-app --startup-file "startup.sh"

# Deploy code
az webapp up --name smart-parking-app --resource-group smart-parking-rg
```

## 📁 Project Structure

```
smart-parking-app/
├── app/
│   ├── __init__.py          # App factory (create_app)
│   ├── db.py                # Database connections
│   ├── setup.py             # Auto-initialization
│   ├── utils.py             # Utility functions
│   ├── routes/
│   │   ├── auth.py          # Authentication routes
│   │   ├── customer.py      # Customer views
│   │   ├── owner.py         # Owner views
│   │   └── api.py           # REST API endpoints
│   └── services/
│       └── db_setup.py      # Schema constants
├── templates/               # HTML templates
├── static/                  # CSS/JS/images
├── data/
│   └── ml_training/         # ML models & training data
├── instance/                # Database files (auto-created)
├── run.py                   # Application entry point
├── requirements.txt         # Python dependencies
├── Dockerfile               # Docker configuration
├── startup.sh               # Azure startup script
├── .github/workflows/       # CI/CD pipeline
└── README.md                # This file
```

## 📦 What Gets Installed

### Python Packages (from requirements.txt)

**Core Framework:**
- Flask 3.1.2 - Web framework
- Flask-SocketIO 5.5.1 - Real-time WebSocket support

**ML/AI:**
- scikit-learn 1.6.1 - Machine learning models
- numpy 2.3.4 - Numerical computing
- pandas 2.3.3 - Data manipulation

**Production Server:**
- gunicorn - WSGI HTTP server
- eventlet - Async networking library

**Database:**
- SQLite3 - Built into Python (no install needed!)

### Project Files Auto-Created

**On First Run:**
```
instance/
  ├── parking.db      # Main database (created automatically)
  └── demo.db         # Demo data (created automatically)
```

**ML Models (Pre-trained):**
```
data/ml_training/
  ├── occupancy_model.pkl     # Predicts parking occupancy
  ├── pricing_model.pkl       # Dynamic pricing recommendations
  ├── forecasting_model.pkl   # Peak hours prediction
  └── preference_model.pkl    # User spot recommendations
```

Everything auto-initializes - just run `python run.py`!

## 🧪 Testing

```bash
# Run application tests
python -m pytest tests/

# Check for code issues
python pre_deployment_check.py
```

## 📦 Requirements

Key dependencies (see `requirements.txt` for full list):

```
Flask==3.1.2
Flask-SocketIO==5.5.1
gunicorn
eventlet
scikit-learn==1.6.1
pandas==2.3.3
numpy==2.3.4
joblib==1.4.2
python-dotenv==1.2.1
Werkzeug==3.1.3
```

### Installing Specific Versions

```bash
# Core Flask
pip install Flask==3.1.2

# Real-time features
pip install Flask-SocketIO==5.5.1 python-socketio==5.14.3 eventlet

# ML/AI
pip install scikit-learn==1.6.1 pandas==2.3.3 numpy==2.3.4

# Production server
pip install gunicorn
```

## 🆘 Common Issues & Fixes

### "Port 5000 already in use"

**Windows:**
```bash
netstat -ano | findstr :5000
taskkill /PID <PID> /F
```

**Linux/macOS:**
```bash
lsof -ti:5000 | xargs kill -9
```

### "Module not found" or Import Errors

```bash
# Make sure virtual environment is activated
# You should see (.venv) in terminal prompt

# Reinstall dependencies
pip install --upgrade -r requirements.txt
```

### "Python not found"

Make sure Python is in PATH:
- Windows: Reinstall Python with "Add to PATH" checked
- Linux/Mac: Use `python3` instead of `python`

### Database Won't Create

```bash
# Create instance folder manually
mkdir instance

# Run app again
python run.py
```

### VS Code Not Finding Python

1. Press `Ctrl+Shift+P`
2. Type: `Python: Select Interpreter`
3. Choose `.venv/Scripts/python.exe` (Windows) or `.venv/bin/python` (Linux/Mac)

### Can't Activate Virtual Environment (Windows)

If you get "execution policy" error:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

Then try activating again:
```bash
.venv\Scripts\activate
```

## 📝 License

This project is for educational purposes.

## 👥 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/YourFeature`)
3. Commit changes (`git commit -m 'Add YourFeature'`)
4. Push to branch (`git push origin feature/YourFeature`)
5. Open Pull Request

## 📧 Contact

- **GitHub:** [@DefinitelyNotABot-del](https://github.com/DefinitelyNotABot-del)
- **Live App:** https://smart-parking-app.azurewebsites.net
