# 🗄️ Two-Database Architecture

## Why Two Databases?

Your Smart Parking app now uses **two separate SQLite databases** to isolate demo data from real user data:

```
┌─────────────────────────────────────┐
│  demo.db (77 KB)                    │
│  - Demo accounts only               │
│  - Pre-loaded with 318 bookings     │
│  - 4 lots, 545 spots                │
│  - Deploys with the app             │
│  - Never gets reset                 │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│  parking.db (Empty)                 │
│  - All regular users                │
│  - Starts empty                     │
│  - Users create own data            │
│  - Can be reset anytime             │
│  - Ignored by git                   │
└─────────────────────────────────────┘
```

## 🎯 How It Works

### Demo Account Login
```python
Email: demo.owner@smartparking.com
Password: demo123
→ Connects to demo.db
→ Sees 4 lots with full analytics
→ Pre-loaded bookings
```

### Regular User Registration
```python
Email: john@example.com
Password: mypassword
→ Connects to parking.db
→ Starts with empty dashboard
→ Creates own lots and data
```

## 🚀 Deployment Strategy

### Local Development
```bash
# Both databases exist
demo.db      → Keep in git (pre-loaded)
parking.db   → In .gitignore (user data)
```

### Production Deployment
```bash
# Deploy demo.db with the app
git add demo.db
git commit -m "Add demo database"
git push

# parking.db is created automatically on first run
# Users can wipe parking.db without affecting demos
```

## 🔐 Data Isolation

The app automatically routes queries to the correct database:

```python
# In app.py
def get_db():
    if session.get('is_demo'):
        return sqlite3.connect('demo.db')
    else:
        return sqlite3.connect('parking.db')
```

## 📝 Setup Instructions

### First Time Setup
```bash
python complete_setup.py
```
This creates:
- ✅ `demo.db` with pre-loaded data (77 KB)
- ✅ `parking.db` empty (for users)

### Reset User Data (Keep Demos)
```bash
rm parking.db
python -c "from app import app; app.app_context().push(); from app import init_db; init_db()"
```

### Reset Everything
```bash
rm demo.db parking.db
python complete_setup.py
```

## 🎓 Benefits

✅ **Demo accounts always work** - Never affected by user actions
✅ **Safe deployment** - Can reset user DB without breaking demos
✅ **Performance** - Each DB stays smaller and faster
✅ **Testing** - Easy to wipe test data, keep demos
✅ **Git-friendly** - demo.db commits, parking.db doesn't

## 📊 Database Stats

| Database | Size | Users | Lots | Spots | Bookings |
|----------|------|-------|------|-------|----------|
| demo.db  | 77 KB | 4 | 4 | 545 | 318 |
| parking.db | Dynamic | ∞ | User-created | User-created | User-created |

---

**Now your demo accounts are safe from any database resets! 🎉**
