# Smart Parking App

This is a full-stack web application designed to streamline the process of finding and managing parking for both customers and parking lot owners.

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

- **AI-Powered Smart Search:** Find parking spots using natural language queries (powered by Google Gemini).
- **Interactive Map:** Visualize parking lot locations with Leaflet.js.
- **Real-time Booking:** Book available parking spots instantly.
- **Multiple Bookings:** Manage multiple active parking sessions.
- **Live Updates:** Real-time spot availability via WebSockets.

### Owner Dashboard

- **CRUD for Parking Lots:** Add, edit, and delete parking lots with ease.
- **Interactive Map:** Precisely select lot coordinates on an interactive map.
- **Spot Management:** Add, edit, and delete individual spots within a lot.
- **Visual Analytics:** View occupancy charts and statistics.
- **Real-time Dashboard:** Monitor all lots with live updates.

### Technical Features

- **Dual Database Support:** SQLite (development) or PostgreSQL (production).
- **Cloud-Ready:** Optimized for Google Cloud Run and Azure deployment.
- **Docker Support:** Containerized for easy deployment.
- **Secure:** Environment-based secrets, API key protection.
- **Tested:** Comprehensive test suite included.

## Deployment

### Deploy to Google Cloud Platform (Recommended)

**Free Tier Benefits:**
- 2 million requests/month free
- Auto-scaling from 0
- No cost when idle

**Quick Deploy:**
```bash
# See detailed guide
cat DEPLOY_GCP.md

# Or run the deployment script
bash deploy-gcp.sh
```

📖 **Full Guide:** [DEPLOY_GCP.md](./DEPLOY_GCP.md)

### Run with Docker

```bash
# Build image
docker build -t smart-parking-app .

# Run container
docker run -p 8080:8080 -e GEMINI_API_KEY=your_key smart-parking-app
```

## Testing

Run the comprehensive test suite:

```bash
# Start the app first
python app.py

# In another terminal, run tests
python test_flows.py
```
