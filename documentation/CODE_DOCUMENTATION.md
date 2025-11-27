# Smart Parking App - Complete Code Documentation

## Document Purpose
This document provides **line-by-line explanations** of all code in the Smart Parking App, explaining **why each line exists** and **how it contributes to the overall functionality**. This is intended for academic review, teammate onboarding, and future maintenance.

---

## Table of Contents
1. [Customer Dashboard (customer.html)](#1-customer-dashboard-customerhtml)
2. [Login Page (index.html)](#2-login-page-indexhtml)
3. [Utility Functions (utils.py)](#3-utility-functions-utilspy)
4. [API Routes (api.py)](#4-api-routes-apipy)
5. [Database Layer (db.py)](#5-database-layer-dbpy)
6. [CSS Styling (style.css)](#6-css-styling-stylecss)

---

## 1. Customer Dashboard (customer.html)

### File Location: `templates/customer.html`

This is the main customer interface where users search for parking spots and view their bookings on an interactive map.

### HTML Head Section

```html
<!DOCTYPE html>
<html lang="en">
```
- **`<!DOCTYPE html>`**: Declares this as an HTML5 document. Required for browsers to render the page in standards mode rather than quirks mode.
- **`<html lang="en">`**: Root element with language attribute set to English. This helps screen readers pronounce content correctly and improves SEO.

```html
<head>
    <meta charset="UTF-8">
```
- **`<meta charset="UTF-8">`**: Specifies UTF-8 character encoding. This allows the page to display characters from virtually any language, including special symbols like ₹ (rupee sign) used in pricing.

```html
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
```
- **Viewport meta tag**: Critical for responsive design. 
  - `width=device-width`: Sets viewport width to match device screen width
  - `initial-scale=1.0`: Prevents automatic zooming on mobile devices
  - Without this, mobile browsers would render the page as if it were a desktop site and scale it down

```html
    <title>Customer - Smart Parking</title>
```
- **Title tag**: Appears in browser tab and bookmarks. "Customer - Smart Parking" clearly identifies this as the customer-facing part of the app.

```html
    <link rel="stylesheet" href="https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css">
```
- **Bootstrap 4.5.2 CSS**: Provides pre-built responsive grid system, form styling, buttons, cards, and utility classes. We use Bootstrap 4 (not 5) because it's stable and widely supported.

```html
    <link rel="stylesheet" href="https://unpkg.com/leaflet/dist/leaflet.css" />
```
- **Leaflet CSS**: Required for the interactive map. Contains styles for map tiles, markers, popups, and zoom controls. Must be loaded before Leaflet JS.

```html
    <script src="https://cdn.socket.io/4.7.5/socket.io.min.js"></script>
```
- **Socket.IO Client Library**: Enables real-time bidirectional communication with the server. Used for live updates when parking spot availability changes. Version 4.7.5 is current and compatible with our Flask-SocketIO backend.

```html
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;700&display=swap" rel="stylesheet">
```
- **Google Fonts Preconnect & Load**: 
  - `preconnect` hints tell the browser to establish early connections to font servers, reducing load time
  - `crossorigin` is required for fonts.gstatic.com due to CORS requirements
  - We load Poppins font in three weights (400=regular, 500=medium, 700=bold) for consistent, modern typography

```html
    <link rel="stylesheet" href="{{ url_for('static', filename='css/style.css') }}">
```
- **Custom CSS**: Flask's `url_for()` generates the correct path to our static files, handling URL prefixes correctly whether running locally or on Azure.

### Inline CSS Styles

```html
<style>
    body, html {
        height: 100%;
        margin: 0;
    }
```
- **Full-height body**: Sets both `body` and `html` to 100% height so the map can fill the entire viewport.
- **Zero margin**: Removes default browser margins that would create unwanted gaps.

```css
    #map {
        position: absolute;
        left: 0;
        top: 0;
        bottom: 0;
        right: 30vw;
    }
```
- **Map Container Positioning**:
  - `position: absolute`: Removes map from normal document flow, allowing precise positioning
  - `left: 0; top: 0; bottom: 0`: Pins map to left edge and stretches from top to bottom
  - `right: 30vw`: **KEY DESIGN DECISION** - Leaves 30% of viewport width for the sidebar on the right
  - `vw` (viewport width) unit ensures the map-to-sidebar ratio stays consistent on any screen size

```css
    .sidebar {
        position: fixed;
        right: 0;
        top: 0;
        width: 30vw;
        min-width: 300px;
        max-width: 420px;
        height: 100%;
        background-color: white;
        border-left: 1px solid #dee2e6;
        overflow-y: auto;
        z-index: 1000;
        padding: 10px;
    }
```
- **Sidebar Positioning Explained Line by Line**:
  - `position: fixed`: Keeps sidebar in place even during scroll (though our page doesn't scroll). Fixed elements are positioned relative to the viewport, not the document.
  - `right: 0`: Anchors sidebar to the right edge of the viewport
  - `top: 0; height: 100%`: Stretches sidebar from top to bottom of viewport
  - `width: 30vw`: Matches the space we reserved by setting `#map { right: 30vw }`
  - `min-width: 300px`: **Responsive safeguard** - On screens narrower than 1000px, 30vw would be less than 300px, making sidebar unusable. This floor prevents that.
  - `max-width: 420px`: **Large screen safeguard** - On 4K monitors (3840px), 30vw = 1152px, which is too wide. This cap keeps sidebar reasonable.
  - `background-color: white`: Solid background prevents map from showing through
  - `border-left: 1px solid #dee2e6`: Subtle gray line visually separates sidebar from map. Color matches Bootstrap's default border color.
  - `overflow-y: auto`: Enables vertical scrolling if content exceeds sidebar height
  - `z-index: 1000`: Ensures sidebar appears above the map (Leaflet uses z-index values up to 400 for its elements)
  - `padding: 10px`: Adds breathing room around content. Reduced from typical 20px to maximize usable space in narrow sidebar.

```css
    .sidebar .card,
    .sidebar .card .card-body {
        width: 100%;
        box-sizing: border-box;
        margin: 6px 0;
    }
```
- **Card Sizing**:
  - `width: 100%`: Cards fill entire sidebar width
  - `box-sizing: border-box`: **Critical CSS rule** - Includes padding and border in the 100% width calculation. Without this, a card with 10px padding on each side would be 100% + 20px, causing horizontal overflow.
  - `margin: 6px 0`: Vertical spacing between cards (6px top and bottom, 0 left and right)

```css
    .sidebar .card .card-body { padding: 10px 12px; }
```
- **Reduced Card Padding**: Bootstrap's default card-body padding is 20px. We reduce it to save space in our narrow sidebar while keeping content readable.

```css
    .sidebar h3 { font-size: 1.25rem; margin-bottom: 0.5rem; }
```
- **Smaller Headers**: Default h3 is ~1.75rem. Reducing to 1.25rem keeps headers prominent but saves vertical space. Tighter bottom margin (0.5rem vs default 1rem) also saves space.

### HTML Body Structure

```html
<body>
    <div id="map"></div>
```
- **Map Container**: Empty div that Leaflet will populate with map tiles, controls, and markers. Must exist before Leaflet initializes.

```html
    <div class="sidebar">
        <div class="card mb-3">
            <div class="card-body">
                <h5 id="userNameDisplay" class="d-inline-block"></h5>
                <button id="logoutBtn" class="btn btn-secondary btn-sm float-right">Logout</button>
            </div>
        </div>
```
- **User Info Card**:
  - `mb-3`: Bootstrap utility class for margin-bottom (1rem = 16px)
  - `d-inline-block`: Displays username inline so logout button can float beside it
  - `btn-secondary`: Gray button color (not primary action)
  - `btn-sm`: Smaller button to not dominate the header
  - `float-right`: Positions logout button on the right side of the card

```html
        {% if session.get('is_demo') %}
        <div class="alert alert-warning alert-dismissible fade show" role="alert">
            <strong>🎯 Demo Mode</strong> - Pre-generated data available!
            <button type="button" class="close" data-dismiss="alert">&times;</button>
        </div>
        {% endif %}
```
- **Demo Mode Banner (Jinja2 Conditional)**:
  - `{% if session.get('is_demo') %}`: Server-side check if user is logged in with demo account
  - `alert-warning`: Yellow/amber background to draw attention
  - `alert-dismissible fade show`: Allows user to close the alert with X button
  - `role="alert"`: Accessibility attribute for screen readers
  - `&times;`: HTML entity for × (multiplication sign used as close button)

### JavaScript Section

```html
<script>
    const map = L.map('map').setView([12.9716, 77.5946], 13);
```
- **Leaflet Map Initialization**:
  - `L.map('map')`: Creates Leaflet map instance in the div with id="map"
  - `.setView([12.9716, 77.5946], 13)`: Centers map on Bangalore, India (12.9716°N, 77.5946°E) with zoom level 13
  - Zoom 13 shows approximately a 5km radius, good for city-level parking search

```javascript
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    }).addTo(map);
```
- **OpenStreetMap Tile Layer**:
  - `{s}`: Subdomain placeholder (a, b, or c) for load balancing across tile servers
  - `{z}/{x}/{y}`: Zoom level, x-coordinate, y-coordinate of each tile
  - `attribution`: **Legally required** credit to OpenStreetMap contributors (their license requires this)
  - `.addTo(map)`: Attaches tile layer to our map instance

```javascript
    let marker;
```
- **Marker Variable**: Declared outside functions so it persists across clicks. When user clicks a booking, we remove the old marker before adding a new one to prevent marker accumulation.

```javascript
    function setDefaultTimeWindow() {
        const now = new Date();
        const start = new Date(now.getTime() + 15 * 60000);
        const end = new Date(start.getTime() + 60 * 60000);
```
- **Default Booking Time Window**:
  - `new Date()`: Current time in user's timezone
  - `15 * 60000`: 15 minutes in milliseconds (60000ms = 1 minute)
  - Start time: 15 minutes from now (gives user time to reach parking)
  - End time: 1 hour after start (common parking duration)

```javascript
        const toLocalInput = (date) => {
            const tzOff = date.getTimezoneOffset();
            const adjusted = new Date(date.getTime() - (tzOff * 60000));
            return adjusted.toISOString().slice(0, 16);
        };
```
- **Date Formatting for datetime-local Input**:
  - HTML datetime-local inputs require format: "YYYY-MM-DDTHH:MM"
  - `getTimezoneOffset()`: Returns offset from UTC in minutes (e.g., -330 for IST)
  - We adjust the date to create a "fake UTC" that when formatted looks like local time
  - `.slice(0, 16)`: Takes "2025-11-26T14:30" from "2025-11-26T14:30:00.000Z"

```javascript
    async function updateCustomerPage() {
        try {
            const userResponse = await fetch('/api/me');
            if (!userResponse.ok) {
                if (userResponse.status === 401) window.location.href = '/login';
                return;
            }
```
- **User Info Fetch with Auth Handling**:
  - `async/await`: Modern JavaScript syntax for handling promises
  - `fetch('/api/me')`: Gets current logged-in user info
  - `!userResponse.ok`: True for any non-2xx HTTP status
  - `status === 401`: Unauthorized - session expired or not logged in
  - Redirect to login page prevents showing broken page to logged-out users

```javascript
            // Fetch bookings
            const bookingsResponse = await fetch('/api/customer/bookings');
            // ...
            bookings.forEach(booking => {
                const bookingEl = document.createElement('div');
                bookingEl.className = 'booking-item card bg-light mb-2';
                bookingEl.style.cursor = 'pointer';
```
- **Booking Card Creation**:
  - `createElement('div')`: Programmatically create DOM element
  - `bg-light`: Light gray background (Bootstrap class)
  - `cursor: pointer`: Changes mouse cursor to hand on hover, indicating clickability

```javascript
                bookingEl.addEventListener('click', () => {
                    const lat = booking.latitude || booking.lat;
                    const lng = booking.longitude || booking.lon;
                    if (lat && lng) {
                        const latlng = [parseFloat(lat), parseFloat(lng)];
                        map.setView(latlng, 15);
                        if (marker) map.removeLayer(marker);
                        marker = L.marker(latlng).addTo(map)
                            .bindPopup(`<strong>${booking.location}</strong>`).openPopup();
                    }
                });
```
- **Click-to-Map-Pan Handler**:
  - `booking.latitude || booking.lat`: Handles both naming conventions that might exist in API response
  - `parseFloat()`: Ensures coordinates are numbers, not strings
  - `setView(latlng, 15)`: Zoom level 15 shows approximately a 1km radius, good for seeing exact parking location
  - `if (marker) map.removeLayer(marker)`: Removes previous marker to prevent clutter
  - `bindPopup().openPopup()`: Shows location name in a popup bubble immediately

```javascript
        setTimeout(() => { 
            if (map && map.invalidateSize) map.invalidateSize(true); 
        }, 300);
```
- **Leaflet Size Recalculation**:
  - `setTimeout(..., 300)`: Waits 300ms for CSS to fully apply
  - `invalidateSize(true)`: Forces Leaflet to recalculate container dimensions
  - The `true` parameter animates the size change for smoother UX
  - **Why needed**: Leaflet caches container size at init. Our CSS sets final size, but if Leaflet initialized before CSS applied, tiles won't render correctly.

### WebSocket Section

```javascript
    const socket = io();

    socket.on('status_change', function(data) {
        console.log('Status change received:', data);
    });
```
- **Socket.IO Connection**:
  - `io()`: Connects to the same host that served the page (no URL needed)
  - `socket.on('status_change', ...)`: Listens for parking spot status changes
  - Real-time updates allow seeing availability changes without page refresh

---

## 2. Login Page (index.html)

### File Location: `templates/index.html`

### Key Styling

```css
.login-container {
    max-width: 400px;
    margin: 100px auto;
}
```
- **Centered Login Card**:
  - `max-width: 400px`: Limits card width for readability (optimal line length)
  - `margin: 100px auto`: 100px top margin for visual breathing room; `auto` left/right centers the card

### Demo Credentials Display

```html
<div id="demoInfo" style="display:none;" class="alert alert-light mt-2 small text-left">
    <div class="mb-1"><strong>Owner:</strong> <span id="demoOwnerEmail">demo.owner@smartparking.com</span></div>
    <div class="mb-1"><strong>Customer:</strong> <span id="demoCustomerEmail">demo.customer@smartparking.com</span></div>
    <div class="mb-0"><strong>Password:</strong> <span id="demoPassword">demo123</span></div>
</div>
```
- **Collapsible Demo Info**:
  - `display:none`: Hidden by default, revealed on click
  - `alert-light`: Subtle background that doesn't distract from main form
  - `small`: Smaller font size for supplementary information
  - **Design Decision**: We removed autofill/copy buttons for production stability. Manual typing is more reliable.

### Login Form Handler

```javascript
document.getElementById('login-form').addEventListener('submit', async (e) => {
    e.preventDefault();
```
- **Form Submit Prevention**:
  - `e.preventDefault()`: Stops browser's default form submission (which would reload the page)
  - We handle submission with JavaScript for better UX (no page reload, inline error messages)

```javascript
    const urlParams = new URLSearchParams(window.location.search);
    const role = urlParams.get('role');
```
- **Role Extraction from URL**:
  - If user came from role selection page with `?role=customer`, we pass that role to the backend
  - This allows the same credentials to log in as different roles (owner can also view as customer)

---

## 3. Utility Functions (utils.py)

### File Location: `app/utils.py`

### IST Timezone Handling

```python
from datetime import datetime, timedelta, timezone

IST = timezone(timedelta(hours=5, minutes=30))
```
- **IST Timezone Constant**:
  - India Standard Time is UTC+5:30
  - `timezone(timedelta(hours=5, minutes=30))`: Creates a timezone object representing +05:30
  - Using a constant ensures consistent timezone handling throughout the app

```python
def get_ist_now():
    """Get current time in IST timezone"""
    return datetime.now(IST)
```
- **IST-Aware Current Time**:
  - `datetime.now(IST)`: Returns current time with IST timezone attached
  - **Why needed**: Azure servers run on UTC. Without explicit timezone, `datetime.now()` returns server time, causing booking time mismatches for Indian users.

### Price Coercion

```python
def coerce_price(value, fallback):
    try:
        if value is None or value == "": 
            return round(float(fallback), 2)
        price = float(value)
        if price < 0: 
            raise ValueError("Price must be non-negative")
        return round(price, 2)
    except (TypeError, ValueError):
        current_app.logger.warning(f"Invalid price input '{value}', using fallback {fallback}")
        return round(float(fallback), 2)
```
- **Defensive Price Handling**:
  - Handles None, empty string, invalid types, negative numbers
  - `round(..., 2)`: Currency values should have exactly 2 decimal places
  - Logs warnings for debugging but doesn't crash the app
  - **Why**: User input is unpredictable. This function prevents NaN or null prices from corrupting the database.

### ML Model Loading

```python
def load_model(model_name):
    """Lazy load ML models on-demand."""
    global AI_MODELS
    if model_name in AI_MODELS:
        return AI_MODELS[model_name]
```
- **Lazy Loading Pattern**:
  - Models are only loaded when first needed, not at app startup
  - `global AI_MODELS`: Cache loaded models in module-level dict
  - **Why**: Azure F1 tier has 230-second startup timeout. Loading 31.78 MB of models at startup would exceed this. Lazy loading spreads the load.

```python
    if hasattr(model, 'n_jobs'):
        model.n_jobs = 1  # Critical for Azure F1 tier
```
- **Single-Thread Enforcement**:
  - scikit-learn models can parallelize with `n_jobs=-1`
  - Azure F1 has limited CPU; parallelization causes crashes
  - Setting `n_jobs=1` forces sequential execution

---

## 4. API Routes (api.py)

### File Location: `app/routes/api.py`

### Customer Bookings Endpoint

```python
@api_bp.route('/api/customer/bookings')
def get_customer_bookings():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Not logged in'}), 401
```
- **Authentication Check**:
  - `session.get('user_id')`: Returns None if not logged in
  - 401 Unauthorized: Standard HTTP status for "not authenticated"

```python
    now_iso = get_ist_now().strftime("%Y-%m-%dT%H:%M:%SZ")
    cursor.execute("""
        SELECT b.*, l.name as location, l.latitude, l.longitude, s.type
        FROM bookings b
        JOIN lots l ON b.lot_id = l.lot_id
        JOIN spots s ON b.spot_id = s.spot_id AND b.lot_id = s.lot_id
        WHERE b.user_id = ? AND b.end_time >= ?
        ORDER BY b.start_time ASC
    """, (user_id, now_iso))
```
- **Active Bookings Query Explained**:
  - `b.*`: All columns from bookings table
  - `l.name as location`: Lot name for display
  - `l.latitude, l.longitude`: **Added Nov 26** - Enables click-to-map-pan feature
  - `JOIN lots l ON b.lot_id = l.lot_id`: Links booking to its parking lot
  - `JOIN spots s ON b.spot_id = s.spot_id AND b.lot_id = s.lot_id`: Links to spot for vehicle type
  - `WHERE b.end_time >= ?`: Only bookings that haven't ended yet (active/future)
  - `ORDER BY b.start_time ASC`: Soonest booking first

---

## 5. Database Layer (db.py)

### File Location: `app/db.py`

### Two-Database Architecture

```python
def get_db():
    if 'db' not in g:
        if session.get('is_demo'):
            db_path = os.path.join(current_app.instance_path, 'demo.db')
        else:
            db_path = os.path.join(current_app.instance_path, 'parking.db')
        g.db = sqlite3.connect(db_path)
        g.db.row_factory = sqlite3.Row
    return g.db
```
- **Session-Based Database Routing**:
  - `g`: Flask's application context global, exists for the duration of one request
  - `session.get('is_demo')`: True if logged in with demo credentials
  - **Why two databases?**: 
    - `demo.db`: Pre-populated with Bangalore data, committed to git, survives deployments
    - `parking.db`: Real user data, not in git, starts empty on new deployments
  - `row_factory = sqlite3.Row`: Allows accessing columns by name (e.g., `row['latitude']`) instead of index

---

## 6. CSS Styling (style.css)

### File Location: `static/css/style.css`

### CSS Variables

```css
:root {
    --primary-color: #007bff;
    --secondary-color: #6c757d;
    --success-color: #28a745;
}
```
- **CSS Custom Properties**:
  - Defined on `:root` (document root, equivalent to `html`)
  - Allows consistent theming across the app
  - Easy to change color scheme by modifying these values
  - Usage: `color: var(--primary-color);`

### Responsive Considerations

The customer page uses viewport-relative units (`vw`) for the sidebar, which automatically adapts to screen size. The `min-width` and `max-width` constraints provide guardrails for extreme screen sizes.

---

## Summary of Design Decisions

| Decision | Rationale |
|----------|-----------|
| 30% fixed sidebar | Optimal balance between map visibility and form usability |
| No toggle button | Simpler UX, no state to manage, no visual glitches |
| IST timezone | Target users are in India; server runs on UTC |
| Lazy model loading | Azure F1 has 230-second startup timeout |
| Two databases | Demo data persists through deployments |
| Click-to-pan bookings | Quick visual confirmation of booking location |
| Bootstrap 4 | Stable, well-documented, good browser support |
| Leaflet + OSM | Free, no API keys, open source |

---

## Revision History

| Date | Changes |
|------|---------|
| Nov 26, 2025 | Initial comprehensive documentation |
| Nov 25, 2025 | IST timezone, demo DB updates |
| Nov 23, 2025 | Customer page clickable bookings |
| Nov 15-16, 2025 | Blueprint refactoring |
| Nov 14, 2025 | ML integration |
| Nov 10-11, 2025 | Initial Azure deployment |

---

*This document is for internal use and academic review. Last updated: November 26, 2025.*
