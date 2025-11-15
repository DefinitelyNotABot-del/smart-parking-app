# 🚀 Smart Parking App - Quick Start Guide

## One-Command Deployment ✨

**No setup scripts needed!** The app automatically initializes databases on first run.

### Local Development

```bash
# Just run the app - databases auto-initialize
python run.py
```

**OR with gunicorn (production mode):**
```bash
gunicorn --bind 0.0.0.0:8000 --worker-class eventlet --workers 1 run:app
```

That's it! The app will:
- ✅ Create `instance/` directory
- ✅ Initialize `demo.db` with pre-loaded data
- ✅ Initialize `parking.db` for regular users
- ✅ Set up demo accounts automatically

### Demo Accounts (Pre-loaded)

Access immediately after first run:

**Owner Account:**
- Email: `demo.owner@smartparking.com`
- Password: `demo123`
- Pre-loaded: 4 parking lots, 390 spots

**Customer Account:**
- Email: `demo.customer@smartparking.com`
- Password: `demo123`
- Pre-loaded: Historical booking data

### Cloud Deployment

**Docker:**
```bash
docker build -t smart-parking .
docker run -p 8000:8000 -e PORT=8000 smart-parking
```

**Azure App Service:**
```bash
# Method 1: Push to GitHub (auto-deploys via GitHub Actions)
git push origin main

# Method 2: Azure CLI
az webapp up --name your-app-name --resource-group your-rg --runtime "PYTHON:3.11"
```

**Environment Variables:**
- `PORT` - Port number (auto-set by Azure, default: 8000)
- `FLASK_SECRET_KEY` - Set in Azure portal for production

### What Changed?

**Before (2 steps):**
```bash
python complete_setup.py  # Step 1: Setup databases
python run.py             # Step 2: Run app
```

**Now (1 step):**
```bash
python run.py  # Everything happens automatically!
```

### How It Works

The app uses `app/setup.py` with smart initialization:

1. **First Run:** Detects missing databases → Creates & populates them
2. **Subsequent Runs:** Detects existing databases → Skips setup
3. **Cloud Deployment:** Auto-initializes on first container start

### Verify Before Deployment

Run the pre-deployment check:
```bash
python pre_deployment_check.py
```

This validates:
- ✅ All dependencies installed
- ✅ Flask app can be created
- ✅ Database paths are correct
- ✅ SocketIO configured properly
- ✅ Dockerfile uses eventlet workers
- ✅ Auto-initialization enabled

### Project Structure

```
smart-parking-app-fresh/
├── app/
│   ├── __init__.py          # App factory + auto-init
│   ├── setup.py             # Auto database setup (NEW!)
│   ├── routes/              # API endpoints
│   └── services/            # Business logic
├── instance/                # Created automatically
│   ├── demo.db              # Demo accounts (auto-created)
│   └── parking.db           # Regular users (auto-created)
├── run.py                   # Single entry point
├── Dockerfile               # Production-ready
└── requirements.txt         # All dependencies
```

### Troubleshooting

**Databases not initializing?**
- Check `instance/` directory exists
- Look for "🚀 FIRST TIME SETUP" in console output
- Verify write permissions

**Port conflicts?**
- Change port: `python run.py --port 5001`
- Or with gunicorn: `--bind 0.0.0.0:5001`

**Want to reset demo data?**
```bash
rm instance/demo.db
python run.py  # Will recreate automatically
```

### Key Features

- 🔄 **Auto-initialization:** No manual setup scripts
- 🗄️ **Dual databases:** Separate demo & user data
- 🔌 **Real-time updates:** WebSocket support via SocketIO
- 🤖 **AI models:** Lazy loading for memory efficiency
- 🐳 **Docker-ready:** Single command deployment
- ☁️ **Cloud-optimized:** Azure F1 free tier compatible

---

**Ready to deploy?** Just run `python run.py` and everything works! 🎉
