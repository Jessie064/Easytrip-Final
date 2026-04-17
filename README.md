# Easytrip: Travel Itinerary Planner

Easytrip is a Django-based web application that helps users quickly generate and manage personalized travel itineraries based on their destination, dates, group size, and interests. It integrates with Wikipedia, OpenStreetMap, and Overpass API to fetch real destination data and points of interest.

---

## Features

### Trip Planning
- **Create trips** – Submit a form with destination, trip length (days), group size, start/end dates, and interests
- **Auto-generated itineraries** – Each trip gets day-by-day itinerary placeholders based on trip length
- **Interest-based customization** – Choose from 12 interest categories: Nature, Food, History, Beaches, Nightlife, Shopping, Photography, Architecture, Adventure, Art, Wellness, Markets

### Trip Detail Page
- **Overview** – Wikipedia-sourced summary and highlights for the destination
- **Interactive map** – Leaflet map showing the destination with coordinates
- **Recommended places** – Real points of interest from OpenStreetMap, grouped by your interests (e.g., restaurants, parks, museums)
- **Tabbed navigation** – Overview and Recommended Places tabs

### User Dashboard
- **View all trips** – List of your saved trips, ordered by creation date
- **Recent trips grid** – On the home page for logged-in users
- **Delete trips** – Remove trips from your dashboard

### Authentication
- **Sign up** – Create account (username, email, password)
- **Log in** – Username and password
- **Log out** – End session
- **Optional login** – Unauthenticated users can generate trips; authenticated users can save and access them in a dashboard

### Admin
- **Django admin** – Manage users and data at `/admin/` (requires superuser)

### API
- **Spots by category** – `GET /api/spots/?destination=Cebu City&category=Nature` returns real POIs from OpenStreetMap for a destination and interest category

---

## Functions & Routes

| Route | Function | Description |
|-------|----------|-------------|
| `/` | `home` | Landing page with trip form; shows recent trips for logged-in users |
| `/dashboard/` | `dashboard` | User’s saved trips |
| `/trip/<id>/` | `trip_detail` | Full trip view: overview, itinerary days, map, recommended spots |
| `/trip/<id>/delete/` | `delete_trip` | Delete a trip (redirects to dashboard) |
| `/login/` | `login_view` | Login form |
| `/signup/` | `signup_view` | Registration form |
| `/logout/` | `logout_view` | Logout (redirects to login) |
| `/api/spots/` | `spots_by_category` | API: spots for destination + category |
| `/admin/` | Django admin | Admin panel |

---

## Data Models

### Trip
- `user` (ForeignKey, optional)
- `destination`, `trip_length`, `group_size`
- `start_date`, `end_date`
- `interests` (JSONField)
- `title`, `overview`, `image_url`
- `latitude`, `longitude`
- `created_at`

### ItineraryDay
- `trip` (ForeignKey)
- `day_number`
- `description`

---

## External Services

| Service | Purpose |
|---------|---------|
| **Wikipedia REST API** | Destination overview, spell-corrected titles, coordinates, images |
| **Nominatim (OpenStreetMap)** | Geocoding for lat/lon and bounding boxes |
| **Overpass API** | Real points of interest (restaurants, parks, museums, etc.) by category |
| **Unsplash** | Fallback destination image when Wikipedia has none |

---

## Interest Categories (Overpass filters)

- **Nature** – Parks, nature reserves, peaks, waterfalls  
- **Food** – Restaurants, cafes, fast food  
- **History** – Historic sites, museums  
- **Beaches** – Beaches, marinas  
- **Nightlife** – Bars, nightclubs, pubs  
- **Shopping** – Malls, department stores  
- **Photography** – Viewpoints, attractions  
- **Architecture** – Buildings, historic structures  
- **Adventure** – Climbing, sports centres, surfing, diving  
- **Art** – Museums, galleries, arts centres  
- **Wellness** – Spas, fitness centres  
- **Markets** – Marketplaces, market shops  

---

## Project Structure

```
├── easytrip/           # Django project settings, URLs, WSGI/ASGI
├── planner/            # Main app: models, views, urls
├── templates/          # home.html, dashboard.html, detail.html, login.html, signup.html, base.html
├── static/             # CSS, images
├── manage.py
├── requirements.txt
└── db.sqlite3          # SQLite database (local dev)
```

---

## Setup

1. **Clone and enter project**
   ```bash
   cd jamesdjango
   ```

2. **Create virtual environment**# ✈️ Easytrip — AI-Powered Travel Planner

Easytrip is a Django-based web application that helps users generate and manage personalized travel itineraries in seconds. Powered by AI (Groq / LLaMA), it creates detailed day-by-day plans based on your destination, dates, group size, interests, and budget. It integrates with Wikipedia, OpenStreetMap, Overpass API, and Mapbox for rich destination data and interactive maps.

---

## ✨ Features

### 🗺️ Trip Planning
- **Create trips** — Submit a form with destination, trip length, group size, start/end dates, interests, and optional budget
- **AI-generated itineraries** — Click "Generate My Itinerary" on the trip detail page to get a full day-by-day plan powered by Groq (LLaMA 3.3)
- **Morning / Afternoon / Evening structure** — Each day is broken into time periods with activity name, description, duration, and cost estimate
- **Local tips** — Each day includes an insider tip for that location
- **Estimated daily cost** — AI provides a cost estimate per person per day
- **Regenerate anytime** — Don't like the itinerary? Regenerate it with one click
- **Interest-based customization** — Choose up to 5 from 12 interest categories

### 📍 Trip Detail Page
- **Overview tab** — Wikipedia-sourced destination summary with interest pills
- **Day-by-Day Itinerary tab** — AI-generated accordion-style itinerary
- **Recommended Places tab** — Real POIs from OpenStreetMap grouped by interest
- **Mapbox map** — Interactive map with destination marker (streets + outdoors styles)
- **Budget sidebar** — Budget breakdown with overspend warning
- **Trip info sidebar** — Days, group size, interests at a glance

### 🌍 Home Page
- **Kayak-inspired UI** — Full-width hero with parallax scrolling
- **Hero search bar** — Destination autocomplete with popular suggestions
- **Scroll progress bar** — Teal progress indicator at the top
- **Fade-in animations** — Sections animate in as you scroll
- **Explore grid** — Click popular destinations to auto-fill the form
- **My Recent Trips** — Quick access to your last 4 trips (logged-in users)

### 👤 User Dashboard
- **View all trips** — Full list of saved trips ordered by creation date
- **Delete trips** — Remove trips with confirmation
- **Trip cards** — Image, title, overview, dates, group size

### 🔐 Authentication
- **Sign up** — Username, required email, password (email required for notifications)
- **Log in / Log out** — Standard session-based auth
- **Guest access** — Unauthenticated users can generate trips; authenticated users can save and manage them

### ✉️ Email Notifications
- **Trip confirmation email** — Sent automatically when a logged-in user creates a trip
- **Beautiful HTML email** — Includes destination image, trip details card, interest tags, overview excerpt, and a "View My Itinerary" CTA button
- **Gmail SMTP** — Sent via your Gmail account using an App Password

### 🌙 Dark Mode
- **Toggle** — Click the moon/sun icon in the navbar
- **Persistent** — Preference saved in `localStorage`
- **Fully themed** — All components, cards, forms, and maps adapt

### 🗺️ Spots Discovery
- **Interest checkboxes** — Selecting an interest fetches real POIs from OpenStreetMap live
- **Spots panel** — Shows spot name, type, rating, and map link
- **API endpoint** — `GET /api/spots/?destination=Cebu&category=Nature`

---

## 🔗 Routes

| Route | Function | Description |
|-------|----------|-------------|
| `/` | `home` | Landing page with trip form and recent trips |
| `/dashboard/` | `dashboard` | User's saved trips |
| `/trip/<id>/` | `trip_detail` | Full trip: overview, itinerary, map, spots |
| `/trip/<id>/delete/` | `delete_trip` | Delete a trip |
| `/trips/<id>/generate-itinerary/` | `generate_itinerary` | AI itinerary generation (POST) |
| `/login/` | `login_view` | Login form |
| `/signup/` | `signup_view` | Registration form |
| `/logout/` | `logout_view` | Logout |
| `/api/spots/` | `spots_by_category` | OSM POIs for destination + category |
| `/admin/` | Django admin | Admin panel |

---

## 🗄️ Data Models

### Trip
| Field | Type | Description |
|-------|------|-------------|
| `user` | ForeignKey | Owner (optional) |
| `destination` | CharField | Trip destination |
| `trip_length` | IntegerField | Number of days |
| `group_size` | CharField | e.g. "2 adults" |
| `start_date` / `end_date` | DateField | Trip dates |
| `interests` | JSONField | List of interest categories |
| `budget_total` | DecimalField | Total budget |
| `budget_currency` | CharField | e.g. PHP, USD |
| `budget_breakdown` | JSONField | Per-category budget |
| `title` | CharField | Auto-generated title |
| `overview` | TextField | Wikipedia summary |
| `image_url` | URLField | Destination image |
| `latitude` / `longitude` | FloatField | Coordinates |
| `created_at` | DateTimeField | Creation timestamp |

### ItineraryDay
| Field | Type | Description |
|-------|------|-------------|
| `trip` | ForeignKey | Parent trip |
| `day_number` | IntegerField | Day index |
| `description` | TextField | JSON string with full day data (theme, morning, afternoon, evening, tip, cost) |

---

## 🌐 External Services

| Service | Purpose |
|---------|---------|
| **Groq API (LLaMA 3.3)** | AI-generated day-by-day itineraries |
| **Wikipedia REST API** | Destination overview, coordinates, images |
| **Nominatim (OpenStreetMap)** | Geocoding for lat/lon and bounding boxes |
| **Overpass API** | Real POIs by category |
| **Mapbox GL JS** | Interactive destination maps |
| **Gmail SMTP** | Trip confirmation email notifications |
| **Unsplash** | Fallback destination images |

---

## 🎯 Interest Categories

| Category | OSM Data |
|----------|----------|
| 🌿 Nature | Parks, nature reserves, peaks, waterfalls |
| 🍽️ Food | Restaurants, cafes, fast food |
| 🏛️ History | Historic sites, museums |
| 🏖️ Beaches | Beaches, marinas |
| 🎵 Nightlife | Bars, nightclubs, pubs |
| 🛍️ Shopping | Malls, department stores |
| 📸 Photography | Viewpoints, attractions |
| 🏗️ Architecture | Historic buildings, structures |
| 🧗 Adventure | Climbing, sports centres, surfing, diving |
| 🎨 Art | Museums, galleries, arts centres |
| 🧘 Wellness | Spas, fitness centres |
| 🛒 Markets | Marketplaces, market shops |

---

## 📁 Project Structure

```
Easytrip/
├── easytrip/               # Django project settings, URLs, WSGI/ASGI
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── planner/                # Main app
│   ├── models.py           # Trip, ItineraryDay
│   ├── views.py            # All views + API
│   └── urls.py             # URL routing
├── templates/              # HTML templates
│   ├── base.html           # Navbar, footer, dark mode
│   ├── home.html           # Landing page
│   ├── detail.html         # Trip detail page
│   ├── dashboard.html      # User dashboard
│   ├── login.html          # Login page
│   ├── signup.html         # Signup page
│   └── emails/
│       └── trip_created.html  # Trip confirmation email
├── static/
│   └── css/
│       └── style.css       # Kayak-inspired UI + dark mode
├── manage.py
├── requirements.txt
└── db.sqlite3              # SQLite database (local dev)
```

---

## ⚙️ Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/Jessie064/Easytrip.git
   cd Easytrip
   ```

2. **Create and activate virtual environment**
   ```bash
   python -m venv venv
   .\venv\Scripts\Activate.ps1   # Windows
   source venv/bin/activate       # Mac/Linux
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure `settings.py`**
   ```python
   GROQ_API_KEY = 'your-groq-api-key'
   MAPBOX_TOKEN = 'your-mapbox-token'
   SITE_URL = 'http://127.0.0.1:8000'

   EMAIL_HOST_USER = 'your-gmail@gmail.com'
   EMAIL_HOST_PASSWORD = 'your-16-char-app-password'
   DEFAULT_FROM_EMAIL = 'Easytrip ✈️ <your-gmail@gmail.com>'
   ```

5. **Run migrations**
   ```bash
   python manage.py migrate
   ```

6. **Create superuser (optional)**
   ```bash
   python manage.py createsuperuser
   ```

7. **Run the server**
   ```bash
   python manage.py runserver
   ```

8. Open **http://127.0.0.1:8000/**

---

## 🗃️ Database

- **Local**: SQLite (`db.sqlite3`) — no extra setup needed
- **Production**: Set `DATABASE_URL` for PostgreSQL (e.g. `postgres://user:pass@host:5432/dbname`); add `psycopg2-binary` to `requirements.txt`

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Django 6.0, Python 3 |
| AI | Groq API (LLaMA 3.3 70B) |
| Database | SQLite (dev) / PostgreSQL (prod) |
| Maps | Mapbox GL JS |
| Frontend | Vanilla JS, CSS Variables |
| Email | Django SMTP + Gmail |
| Static Files | Whitenoise |
| External APIs | Wikipedia, Nominatim, Overpass, Unsplash |

---

## 👨‍💻 Author

Built by **Pepito** — powered by Django & AI 🚀
   ```bash
   python -m venv venv
   .\venv\Scripts\Activate.ps1   # Windows
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run migrations**
   ```bash
   python manage.py migrate
   ```

5. **Create superuser (optional)**
   ```bash
   python manage.py createsuperuser
   ```

6. **Run server**
   ```bash
   python manage.py runserver
   ```

7. Open **http://127.0.0.1:8000/**

---

## Database

- **Local**: SQLite (`db.sqlite3`) – no extra setup
- **Production**: Set `DATABASE_URL` for PostgreSQL (e.g. `postgres://user:pass@host:5432/dbname`); add `psycopg2-binary` to `requirements.txt` for production deploys

---

## Tech Stack

- Django 6.0
- Python 3
- SQLite (default) / PostgreSQL (via `dj-database-url`)
- Whitenoise (static files)
- Pillow (image handling)
- Leaflet (maps)
- Wikipedia, Nominatim, Overpass APIs
