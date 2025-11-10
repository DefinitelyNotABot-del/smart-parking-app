# 🅿️ Smart Parking App

Real-time parking management with AI-powered search. Deploy to Azure in minutes with $100 free student credits!

## 🚀 Quick Deploy to Azure (Free Tier)

**Cost: $0/month on Free tier** (uses ~$0 of your $100 credit)

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
- `GEMINI_API_KEY` (from Google AI Studio)
- `FLASK_SECRET_KEY` (generate: `python -c "import secrets; print(secrets.token_hex(32))"`)

3. **Deploy:**
```bash
git add .
git commit -m "Configure Azure deployment"
git push origin main
```

Your app will be live at: `https://smart-parking-app.azurewebsites.net`

## 🔒 Security Features

- **Federated Credentials (OIDC)** - No service principal keys stored!
- **Managed Identity** - Azure resources authenticate automatically
- **GitHub Secrets** - All sensitive data encrypted
- **No manual key rotation** - Automatic credential management

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
- `.env`: Environment variables (e.g., `GEMINI_API_KEY`).

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

### 5. Set Up Environment Variables

Create a `.env` file in the root directory of the project and add your `GEMINI_API_KEY`. You can obtain a GEMINI_API_KEY from the Google AI Studio.

```
GEMINI_API_KEY='your_gemini_api_key_here'
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
