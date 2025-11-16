# 🅿️ Smart Parking Management System

AI-powered parking management platform with real-time booking, analytics, and dynamic pricing recommendations.

## 🚀 Live Demo

**URL:** https://smart-parking-app.azurewebsites.net

## ✨ Features

- 🎯 **Smart Search** - NLP-powered natural language parking search
- 🗺️ **Interactive Maps** - Leaflet.js with OpenStreetMap integration
- 📊 **AI Analytics** - ML-based occupancy forecasting and pricing optimization
- 🔄 **Real-time Updates** - WebSocket notifications for spot availability
- 👥 **Dual Roles** - Customer (find & book) and Owner (manage lots)
- 🔒 **Secure Auth** - Password hashing and session management

## 🛠️ Technology Stack

- **Backend:** Flask 3.1.2, Flask-SocketIO 5.5.1, SQLite3
- **Frontend:** HTML5/CSS3/JavaScript, Leaflet.js, Chart.js
- **ML/AI:** Scikit-learn 1.6.1, NumPy, Pandas
- **Server:** Gunicorn + Eventlet (production), Flask dev server (local)
- **Cloud:** Azure App Service (F1 Free Tier)

## 📋 Prerequisites

### Required Software

1. **Python 3.12+**
   - Download: https://www.python.org/downloads/
   - Verify: `python --version`

2. **Git**
   - Download: https://git-scm.com/downloads
   - Verify: `git --version`

3. **Docker** (Optional - for containerized deployment)
   - Download: https://www.docker.com/products/docker-desktop/
   - Verify: `docker --version`

4. **Azure CLI** (Optional - for Azure deployment)
   - Download: https://docs.microsoft.com/en-us/cli/azure/install-azure-cli
   - Verify: `az --version`

## 🚀 Local Setup

### 1. Clone Repository

```bash
git clone https://github.com/DefinitelyNotABot-del/smart-parking-app.git
cd smart-parking-app
```

### 2. Create Virtual Environment

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

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Environment Configuration (Optional)

Create a `.env` file in the project root:

```env
FLASK_SECRET_KEY=your-secret-key-here
FLASK_ENV=development
```

Generate a secure secret key:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### 5. Run Application

**Method 1: Flask Development Server**
```bash
python run.py
```

**Method 2: Gunicorn (Production-like)**
```bash
gunicorn --worker-class eventlet -w 1 --bind 0.0.0.0:5000 "app:create_app()"
```

Access the app at: **http://localhost:5000**

## 🐳 Docker Setup

### Build Docker Image

```bash
docker build -t smart-parking-app .
```

### Run Container

```bash
docker run -d -p 5000:5000 --name parking-app smart-parking-app
```

### Stop Container

```bash
docker stop parking-app
docker rm parking-app
```

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

## 🔧 Configuration

### Database

The app uses **dual SQLite architecture**:
- `instance/parking.db` - Main production database
- `instance/demo.db` - Demo data with pre-populated lots

Databases are created automatically on first run.

### ML Models

Pre-trained models located in `data/ml_training/`:
- `occupancy_model.pkl` - Predicts parking occupancy
- `pricing_model.pkl` - Dynamic pricing recommendations
- `forecasting_model.pkl` - Peak hours prediction
- `preference_model.pkl` - User spot recommendations

Models are loaded on-demand to minimize memory usage.

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

## 🆘 Troubleshooting

### Port Already in Use

```bash
# Windows
netstat -ano | findstr :5000
taskkill /PID <PID> /F

# Linux/macOS
lsof -ti:5000 | xargs kill -9
```

### Database Locked Error

```bash
# Stop all running instances
# Delete instance/*.db-shm and instance/*.db-wal files
# Restart application
```

### Module Not Found

```bash
# Reinstall dependencies
pip install --upgrade -r requirements.txt
```

### Azure Deployment Fails

- Check `startup.txt` points to `startup.sh`
- Verify Python runtime: `az webapp config show --name <app-name> --resource-group <rg-name>`
- View logs: `az webapp log tail --name <app-name> --resource-group <rg-name>`

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
