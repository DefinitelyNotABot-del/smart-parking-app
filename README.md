# 🅿️ Smart Parking App

Real-time parking management with **intelligent local NLP search**. Deployed on Azure with zero-cost Free tier!

## ✨ Key Features

- 🧠 **Smart Local NLP Search** - Understands natural language without external APIs
- 🎯 **No Hallucinations** - Only returns real parking spots from your database
- ⚡ **Instant Results** - No API timeouts, works offline
- 🔄 **Real-time Updates** - WebSocket notifications for spot availability
- 🗺️ **Interactive Map** - Leaflet.js with OpenStreetMap integration
- 👥 **Dual Roles** - Customer (find parking) & Owner (manage lots)
- � **Secure Authentication** - Password hashing with Werkzeug
- 🌐 **Production Ready** - Deployed on Azure App Service

## 🚀 Live Demo

**Deployed at:** https://smart-parking-app.azurewebsites.net

**Cost: $0/month** - Runs on Azure F1 Free tier (no consumption of student credits!)

### Prerequisites
- Azure student account ($100 credit)
- GitHub account
- Git Bash (for Windows)

### Setup (One-Time - 5 minutes)

1. **Run Azure Setup Script:**
```bash
# In Git Bash or Azure Cloud Shell
chmod +x setup-azure.sh
./setup-azure.sh
```

2. **Add GitHub Secrets:**
Go to: `Settings` → `Secrets and variables` → `Actions` → `New repository secret`

Add these 5 secrets from the script output:
- `AZURE_CLIENT_ID`
- `AZURE_TENANT_ID`
- `AZURE_SUBSCRIPTION_ID`
- `FLASK_SECRET_KEY` (generate: `python -c "import secrets; print(secrets.token_hex(32))"`)

3. **Deploy:**
```bash
git add .
git commit -m "Configure Azure deployment"
git push origin main
```

Your app will be live at: `https://smart-parking-app.azurewebsites.net`

## 🔒 Security Features

- **Federated Credentials (OIDC)** - No service principal keys stored anywhere!
- **Managed Identity** - Azure resources authenticate automatically
- **GitHub Secrets** - All sensitive data encrypted
- **No manual key rotation** - Automatic credential management
- **Password Hashing** - Werkzeug secure password storage

## 🧠 Smart NLP Search Engine

### How It Works
The app features a **custom-built local NLP parser** that understands natural language queries without external APIs:

**Example Queries:**
- "I need car parking near AMC Engineering College" ✅
- "bike parking vega city" ✅

**Features:**
- ✅ **Exact Word Matching** - Finds locations with matching keywords
- ✅ **Fuzzy Matching** - Handles typos (60% similarity threshold)
- ✅ **Vehicle Type Detection** - Automatically identifies car/bike
- ✅ **No Hallucinations** - Only returns real spots from database
- ✅ **Instant Response** - No API timeouts or rate limits
- ✅ **Works Offline** - Pure Python regex and fuzzy logic

### Why Local NLP?
We initially used **Google Gemini API**, but encountered issues:
- ❌ Free tier extremely slow (2+ minute response times)
- ❌ Worker timeouts killing requests
- ❌ Rate limits and API key management
- ❌ Dependency on external service

**Solution:** Built lightweight NLP using Python's `difflib` and regex patterns
- ⚡ Instant results (<100ms)
- 💰 Zero API costs
- 🔒 Complete data privacy
- 📈 Scales infinitely

## 🛠️ Technology Stack

**Backend:**
- Flask 3.1.2 (Web framework)
- Flask-SocketIO 5.5.1 (Real-time WebSocket communication)
- SQLite3 (Database - zero configuration)
- Gunicorn + Eventlet (Production server)
- Custom NLP Parser (Local natural language processing)

**Frontend:**
- HTML5/CSS3/JavaScript
- Leaflet.js (Interactive maps)
- Chart.js (Analytics visualization)
- OpenStreetMap (Free map tiles)

**Cloud Infrastructure:**
- Azure App Service F1 (Free tier - $0/month)
- GitHub Actions (CI/CD with OIDC authentication)
- Azure Managed Identity (Secure resource access)

**Security:**
- Werkzeug (Password hashing)
- Environment variables for secrets
- Federated Credentials (No stored keys)

## 📊 What We Accomplished (Latest Session)

### Problem Solved
- **Initial Issue:** Gemini API free tier was timing out (2+ minutes per search)
- **Root Cause:** Azure F1 worker timeout at 120 seconds, Gemini couldn't respond in time
- **Impact:** Users saw "Application Error" - complete feature failure

### Solution Implemented
1. **Built Custom Local NLP Engine**
   - Regex-based vehicle type extraction
   - Word-by-word location matching
   - Fuzzy similarity fallback (60% threshold)
   - Smart scoring system (exact matches get 15 points, fuzzy gets 10)

2. **Deployment Fixes**
   - Added `ENABLE_ORYX_BUILD=true` for dependency installation
   - Configured `eventlet` worker for async support
   - Set proper Gunicorn timeouts (30s)
   - Added health check endpoint

3. **Security Improvements**
   - Rotated leaked Gemini API keys (3 times)
   - Verified no keys in git history
   - Confirmed GitHub Secrets encryption
   - Added API key length validation

4. **Testing & Refinement**
   - Fixed "too strict" matching (rejected valid locations)
   - Fixed "too loose" matching (matched random locations)
   - Balanced to require exact word matches with fuzzy fallback
   - Added debug logging for troubleshooting

### Results
- ✅ Search works instantly (<100ms response time)
- ✅ Zero dependency on external APIs
- ✅ No more timeouts or worker crashes
- ✅ Accurate location matching without hallucinations
- ✅ Production-ready deployment on Azure Free tier

## Project Structure

- `app.py`: The main Flask server.
- `data/parking.db`: The SQLite database.
- `templates/`: Contains all HTML files.
    - `index.html`: Main splash page (login/signup).
    - `customer.html`: Frontend for customers to find and book spots.
    - `owner.html`: Frontend for owners to add lots/spots and see reports.
    - `lot_spots.html`: Frontend for owners to manage spots within a specific lot.
    - `role.html`: Page for users to select their role (Customer or Owner).
- `requirements.txt`: Lists all Python dependencies.

## Setup Instructions

Follow these steps to get the project running on your local machine:

### 1. Clone the Repository

```bash
git clone <repository_url>
cd smart-parking-app
```

### 2. Create a Virtual Environment

It's recommended to use a virtual environment to manage project dependencies.

```bash
python -m venv .venv
```

### 3. Activate the Virtual Environment

- **On Windows:**
    ```bash
    .venv\Scripts\activate
    ```
- **On macOS/Linux:**
    ```bash
    source .venv/bin/activate
    ```

### 4. Install Dependencies

Install all required Python packages using `pip`:

```bash
pip install -r requirements.txt
```


### 6. Run the Application

Once the dependencies are installed and environment variables are set, you can run the Flask application:

```bash
flask run
```

The application should now be running on `http://127.0.0.1:5000/`.

## Usage

- Open your web browser and navigate to `http://127.0.0.1:5000/`.
- Select your role (Customer or Owner).
- Register or log in to access the respective dashboards.

## Features

### Customer Dashboard

- **AI-Powered Smart Search:** Find parking spots using natural language queries.
- **Interactive Map:** Visualize parking lot locations.
- **Real-time Booking:** Book available parking spots.
- **End Parking:** Mark a booked spot as available.

### Owner Dashboard

- **CRUD for Parking Lots:** Add, edit, and delete parking lots.
- **Interactive Map for Lot Location:** Precisely select lot coordinates.
- **Spot Management:** Add, edit, and delete individual spots within a lot.
- **Occupancy Overview:** Monitor total and occupied spots for each lot.
