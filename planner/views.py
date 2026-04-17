from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.db import IntegrityError
from django.http import JsonResponse
from django.conf import settings
from django.core.mail import send_mail
from django.core.cache import cache
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from .models import Trip, ItineraryDay, LoginToken
import datetime
import json
import random
import re
import time
from decimal import Decimal, InvalidOperation
import requests
import urllib.parse
from groq import Groq
from django.urls import reverse

# ---- Login attempt constants ----
MAX_ATTEMPTS = 5
LOCKOUT_SECONDS = 300  # 5 minutes
    

# ---- Email helper ----
def send_email(subject, to_email, html_content):
    """Send email using Resend in production or Gmail SMTP locally."""
    resend_key = getattr(settings, 'RESEND_API_KEY', '')
    from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'Easytrip <onboarding@resend.dev>')

    if resend_key:
        try:
            import resend
            resend.api_key = resend_key
            resend.Emails.send({
                "from": from_email,
                "to": [to_email],
                "subject": subject,
                "html": html_content,
            })
            print(f"[EMAIL] Sent via Resend to {to_email}")
        except Exception as e:
            print(f"[EMAIL ERROR] Resend failed: {e}")
    else:
        try:
            plain = strip_tags(html_content)
            send_mail(
                subject=subject,
                message=plain,
                from_email=from_email,
                recipient_list=[to_email],
                html_message=html_content,
                fail_silently=False,
            )
            print(f"[EMAIL] Sent via Gmail SMTP to {to_email}")
        except Exception as e:
            print(f"[EMAIL ERROR] Gmail SMTP failed: {e}")


# ---- Spot rating helper ----
def _spot_rating(name):
    h = sum(ord(c) for c in (name or '')) % 100
    return round(3.5 + (h / 100) * 1.5, 1)


CATEGORY_MAPBOX = {
    'Nature': ['park', 'nature_reserve', 'garden', 'outdoors'],
    'Food': ['restaurant', 'coffee', 'food_and_drink'],
    'History': ['museum', 'monument', 'historic_site'],
    'Beaches': ['beach', 'marina', 'surf_spot'],
    'Nightlife': ['bar', 'nightclub', 'nightlife'],
    'Shopping': ['shopping_mall', 'department_store', 'shopping'],
    'Photography': ['tourist_attraction', 'viewpoint'],
    'Architecture': ['tourist_attraction', 'historic_site', 'monument'],
    'Adventure': ['sports', 'climbing', 'surf_spot', 'scuba_diving_shop'],
    'Art': ['museum', 'art_gallery', 'art'],
    'Wellness': ['spa', 'fitness_center', 'yoga_studio'],
    'Markets': ['market', 'supermarket'],
}


def _mapbox_geocode(destination, token):
    """Geocode a destination using Mapbox Geocoding API v6. Returns (lon, lat, bbox) or None."""
    geo_url = (
        f"https://api.mapbox.com/search/geocode/v6/forward"
        f"?q={urllib.parse.quote(destination)}&limit=1&access_token={token}"
    )
    geo_resp = requests.get(geo_url, timeout=8)
    geo_data = geo_resp.json()
    features = geo_data.get('features', [])
    if not features:
        return None
    feature = features[0]
    coords = feature.get('geometry', {}).get('coordinates', [])
    if len(coords) < 2:
        return None
    lon, lat = coords[0], coords[1]
    bbox = feature.get('properties', {}).get('bbox') or feature.get('bbox')
    if bbox:
        bbox_str = f"{bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]}"
    else:
        d = 0.15
        bbox_str = f"{lon - d},{lat - d},{lon + d},{lat + d}"
    return lon, lat, bbox_str


def _mapbox_category_spots(category_ids, lon, lat, bbox_str, token, limit=20):
    """Fetch POIs from Mapbox Search Box category endpoint. Returns list of spot dicts."""
    spots = []
    seen_names = set()
    for cat_id in category_ids:
        if len(spots) >= limit:
            break
        try:
            url = (
                f"https://api.mapbox.com/search/searchbox/v1/category/{cat_id}"
                f"?proximity={lon},{lat}&bbox={bbox_str}&limit=10"
                f"&access_token={token}"
            )
            resp = requests.get(url, timeout=10)
            data = resp.json()
            for feat in data.get('features', []):
                props = feat.get('properties', {})
                name = props.get('name')
                if not name or name in seen_names:
                    continue
                seen_names.add(name)
                coords = feat.get('geometry', {}).get('coordinates', [])
                poi_cats = props.get('poi_category', [])
                spot_type = poi_cats[0].replace('_', ' ').title() if poi_cats else 'Place'
                spots.append({
                    'name': name,
                    'type': spot_type,
                    'rating': _spot_rating(name),
                    'lat': coords[1] if len(coords) >= 2 else None,
                    'lon': coords[0] if len(coords) >= 2 else None,
                })
                if len(spots) >= limit:
                    break
        except Exception:
            continue
    return spots


def spots_by_category(request):
    destination = request.GET.get('destination', '').strip()
    category = request.GET.get('category', '').strip()

    if not destination or not category:
        return JsonResponse({'error': 'Missing destination or category'}, status=400)

    category_ids = CATEGORY_MAPBOX.get(category, [])
    if not category_ids:
        return JsonResponse({'spots': []})

    token = settings.MAPBOX_TOKEN
    if not token:
        return JsonResponse({'error': 'Mapbox token not configured'}, status=500)

    try:
        result = _mapbox_geocode(destination, token)
        if not result:
            return JsonResponse({'spots': [], 'message': 'Destination not found'})
        lon, lat, bbox_str = result
    except Exception as e:
        return JsonResponse({'error': f'Geocoding failed: {str(e)}'}, status=500)

    try:
        spots = _mapbox_category_spots(category_ids, lon, lat, bbox_str, token, limit=20)
    except Exception as e:
        return JsonResponse({'error': f'Spot search failed: {str(e)}'}, status=500)

    return JsonResponse({'spots': spots, 'category': category, 'destination': destination})


def home(request):
    if request.user.is_authenticated and request.user.is_staff:
        return redirect('monitor_dashboard')
        
    if request.method == 'POST':
        destination = request.POST.get('destination')
        trip_length = request.POST.get('trip_length', 3)
        group_size = request.POST.get('group_size', '1').strip()
        # Format group size nicely
        try:
            gs = int(group_size)
            group_size = f"{gs} {'person' if gs == 1 else 'people'}"
        except (ValueError, TypeError):
            group_size = group_size or '1 person'
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        interests = request.POST.getlist('interests')
        budget_total = request.POST.get('budget_total', '').strip()
        budget_currency = request.POST.get('budget_currency', 'USD').strip()

        def parse_date(date_str):
            if date_str:
                try:
                    return datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
                except ValueError:
                    return None
            return None

        s_date = parse_date(start_date)
        e_date = parse_date(end_date)

        lat = 0.0
        lon = 0.0
        image_url = ''
        search_query = destination

        overview_text = f"Get ready for an amazing adventure in {destination}. This itinerary is tailored to your interests: {', '.join(interests) if interests else 'everything'}."
        try:
            clean_destination = urllib.parse.quote(destination)
            wiki_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{clean_destination}"
            headers = {'User-Agent': 'EasytripApp/1.0'}
            wiki_response = requests.get(wiki_url, headers=headers, timeout=5)
            if wiki_response.status_code == 200:
                wiki_data = wiki_response.json()
                if 'extract' in wiki_data:
                    overview_text = wiki_data['extract']
                if 'title' in wiki_data:
                    search_query = wiki_data['title']
                if 'coordinates' in wiki_data:
                    lat = wiki_data['coordinates']['lat']
                    lon = wiki_data['coordinates']['lon']
                if 'originalimage' in wiki_data:
                    image_url = wiki_data['originalimage']['source']
                elif 'thumbnail' in wiki_data:
                    image_url = wiki_data['thumbnail']['source']
        except Exception as e:
            print(f"Error fetching Wikipedia summary for {destination}: {e}")

        if not image_url or any(kw in image_url.lower() for kw in ['map', 'flag', 'coat', 'locator', 'blank', 'svg']):
            mapbox_token = getattr(settings, 'MAPBOX_TOKEN', '')
            if lat and lon and lat != 0.0 and lon != 0.0 and mapbox_token:
                image_url = f"https://api.mapbox.com/styles/v1/mapbox/outdoors-v12/static/{lon},{lat},10,0/800x400@2x?access_token={mapbox_token}"
            else:
                image_url = "https://images.unsplash.com/photo-1476514525535-07fb3b4ae5f1?auto=format&fit=crop&q=80&w=800"

        try:
            mapbox_token = getattr(settings, 'MAPBOX_TOKEN', '')
            if mapbox_token:
                geo_result = _mapbox_geocode(search_query, mapbox_token)
                if geo_result:
                    lon, lat = geo_result[0], geo_result[1]
        except Exception as e:
            print(f"Error geocoding {search_query}: {e}")

        bt = None
        if budget_total:
            try:
                bt = Decimal(budget_total)
            except (ValueError, TypeError, InvalidOperation):
                pass
        budget_breakdown = {}
        for key in ('accommodation', 'food', 'activities', 'transport'):
            val = request.POST.get(f'budget_{key}', '').strip()
            if val:
                try:
                    budget_breakdown[key] = float(val)
                except (ValueError, TypeError):
                    pass

        trip = Trip.objects.create(
            user=request.user if request.user.is_authenticated else None,
            destination=search_query,
            trip_length=trip_length,
            group_size=group_size,
            start_date=s_date,
            end_date=e_date,
            interests=interests,
            budget_total=bt,
            budget_currency=budget_currency or 'USD',
            budget_breakdown=budget_breakdown,
            title=f"{trip_length} days in {destination}",
            overview=overview_text,
            image_url=image_url,
            latitude=lat,
            longitude=lon
        )

        # Send confirmation email
        if request.user.is_authenticated and request.user.email:
            try:
                html_message = render_to_string('emails/trip_created.html', {
                    'user': request.user,
                    'trip': trip,
                    'site_url': settings.SITE_URL,
                })
                send_email(
                    subject=f'✈️ Your Easytrip itinerary for {trip.destination} is ready!',
                    to_email=request.user.email,
                    html_content=html_message,
                )
            except Exception as e:
                print(f"[EMAIL ERROR] {e}")

        return redirect('trip_detail', trip_id=trip.id)

    if request.user.is_authenticated:
        recent_trips = Trip.objects.filter(user=request.user).order_by('-created_at')[:4]
    else:
        recent_trips = Trip.objects.none()

    context = {'recent_trips': recent_trips}
    return render(request, 'home.html', context)


def trip_detail(request, trip_id):
    trip = get_object_or_404(Trip, id=trip_id)
    days = trip.days.all()

    recommended_spots = []
    token = settings.MAPBOX_TOKEN
    if trip.interests and trip.destination and token:
        try:
            result = _mapbox_geocode(trip.destination, token)
            if result:
                lon, lat, bbox_str = result
                for category in trip.interests[:5]:
                    category_ids = CATEGORY_MAPBOX.get(category, [])
                    if not category_ids:
                        continue
                    try:
                        cat_spots = _mapbox_category_spots(
                            category_ids, lon, lat, bbox_str, token, limit=6
                        )
                        for s in cat_spots:
                            s['category'] = category
                        if cat_spots:
                            recommended_spots.append({'category': category, 'spots': cat_spots})
                    except Exception:
                        continue
        except Exception:
            pass

    breakdown_total = 0
    budget_exceeded = False
    if trip.budget_total and trip.budget_breakdown:
        breakdown_total = sum(
            float(v) for k, v in trip.budget_breakdown.items()
            if isinstance(v, (int, float))
        )
        budget_exceeded = breakdown_total > float(trip.budget_total)

    parsed_days = []
    for day in days:
        try:
            parsed_days.append(json.loads(day.description))
        except (json.JSONDecodeError, TypeError):
            parsed_days.append(None)

    context = {
        'trip': trip,
        'days': days,
        'parsed_days': parsed_days,
        'has_generated': any(d is not None for d in parsed_days),
        'recommended_spots': recommended_spots,
        'budget_exceeded': budget_exceeded,
        'breakdown_total': breakdown_total,
        'mapbox_token': settings.MAPBOX_TOKEN,
    }
    return render(request, 'detail.html', context)


def generate_itinerary(request, trip_id):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
        
    if request.user.is_authenticated and request.user.is_staff:
        return JsonResponse({'error': 'Admins cannot generate plans'}, status=403)

    trip = get_object_or_404(Trip, id=trip_id)

    interests_str = ', '.join(trip.interests) if trip.interests else 'general sightseeing'
    budget_str = f"{trip.budget_currency} {trip.budget_total}" if trip.budget_total else 'unspecified'
    group_str = trip.group_size if trip.group_size else 'a small group'

    prompt = f"""You are an expert travel planner. Generate a detailed {trip.trip_length}-day itinerary for a trip to {trip.destination}.

Trip details:
- Group: {group_str}
- Interests: {interests_str}
- Total Budget: {budget_str}
- Dates: {trip.start_date} to {trip.end_date}

Return ONLY a valid JSON array (no markdown, no explanation) with exactly {trip.trip_length} objects, one per day:
[
  {{
    "day": 1,
    "theme": "Short catchy theme for the day",
    "morning": {{
      "activity": "Activity name",
      "description": "2-3 sentence description with practical details.",
      "duration": "e.g. 2-3 hours",
      "cost": "e.g. Free / $10 per person",
      "transport": {{
        "mode": "e.g. Bus / MRT / Walk / Taxi / Grab",
        "description": "Brief directions to get there",
        "cost": "e.g. $1.50 per person"
      }},
      "food": {{
        "recommendation": "Name of a specific nearby restaurant or food spot",
        "cuisine": "e.g. Local street food / Japanese / Italian",
        "estimated_cost": "e.g. $8-15 per person",
        "must_try": "One specific dish to try"
      }}
    }},
    "afternoon": {{
      "activity": "Activity name",
      "description": "2-3 sentence description.",
      "duration": "e.g. 3 hours",
      "cost": "e.g. $15 per person",
      "transport": {{
        "mode": "e.g. Bus / MRT / Walk / Taxi",
        "description": "Brief directions to get there",
        "cost": "e.g. $2 per person"
      }},
      "food": {{
        "recommendation": "Name of a specific nearby restaurant or food spot",
        "cuisine": "e.g. Local / Fast food / Fine dining",
        "estimated_cost": "e.g. $10-20 per person",
        "must_try": "One specific dish to try"
      }}
    }},
    "evening": {{
      "activity": "Activity name",
      "description": "2-3 sentence description.",
      "duration": "e.g. 2 hours",
      "cost": "e.g. $20-30 per person",
      "transport": {{
        "mode": "e.g. Taxi / Grab / Walk",
        "description": "Brief directions to get there",
        "cost": "e.g. $5 per person"
      }},
      "food": {{
        "recommendation": "Name of a specific restaurant for dinner",
        "cuisine": "e.g. Local / Seafood / International",
        "estimated_cost": "e.g. $15-25 per person",
        "must_try": "One specific dish to try"
      }}
    }},
    "estimated_daily_cost": "e.g. $50-80 per person (including transport & food)",
    "total_transport_cost": "e.g. $10-15 per person",
    "total_food_cost": "e.g. $25-40 per person",
    "local_tip": "One practical insider tip for this day."
  }}
]"""

    try:
        client = Groq(api_key=settings.GROQ_API_KEY)
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=8000,
            temperature=0.7,
        )
        raw_text = completion.choices[0].message.content.strip()

        if raw_text.startswith("```"):
            raw_text = raw_text.split("```")[1]
            if raw_text.startswith("json"):
                raw_text = raw_text[4:]
        raw_text = raw_text.strip()

        # Fix truncated JSON by closing any open brackets
        try:
            days_data = json.loads(raw_text)
        except json.JSONDecodeError:
            # Try to salvage truncated response by closing open brackets
            open_braces = raw_text.count('{') - raw_text.count('}')
            open_brackets = raw_text.count('[') - raw_text.count(']')
            raw_text = raw_text.rstrip(',').rstrip()
            raw_text += '}' * open_braces + ']' * open_brackets
            try:
                days_data = json.loads(raw_text)
            except json.JSONDecodeError as e:
                return JsonResponse({'error': f'Failed to parse AI response: {str(e)}'}, status=500)

        trip.days.all().delete()
        for day in days_data:
            ItineraryDay.objects.create(
                trip=trip,
                day_number=day['day'],
                description=json.dumps(day)
            )

        return JsonResponse({'success': True, 'days': days_data})

    except json.JSONDecodeError as e:
        return JsonResponse({'error': f'Failed to parse AI response: {str(e)}'}, status=500)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def monitor_dashboard(request):
    if not request.user.is_authenticated or not request.user.is_staff:
        return redirect('login')

    from django.db.models import Count, Max
    total_users = User.objects.count()
    total_trips = Trip.objects.count()
    today = timezone.now().date()
    trips_today = Trip.objects.filter(created_at__date=today).count()
    trips_this_week = Trip.objects.filter(
        created_at__date__gte=today - datetime.timedelta(days=7)
    ).count()

    users = User.objects.annotate(
        trip_count=Count('trip'),
        last_trip=Max('trip__created_at')
    ).order_by('-date_joined')

    search_q = request.GET.get('q', '').strip()
    trips = Trip.objects.select_related('user').order_by('-created_at')
    if search_q:
        trips = trips.filter(destination__icontains=search_q) | \
                Trip.objects.filter(user__username__icontains=search_q).order_by('-created_at')

    popular_destinations = (
        Trip.objects.values('destination')
        .annotate(count=Count('destination'))
        .order_by('-count')[:10]
    )

    context = {
        'total_users': total_users,
        'total_trips': total_trips,
        'trips_today': trips_today,
        'trips_this_week': trips_this_week,
        'users': users,
        'trips': trips[:50],
        'popular_destinations': popular_destinations,
        'search_q': search_q,
    }
    return render(request, 'monitor.html', context)


def monitor_user_detail(request, user_id):
    if not request.user.is_authenticated or not request.user.is_staff:
        return redirect('login')
    profile_user = get_object_or_404(User, id=user_id)
    trips = Trip.objects.filter(user=profile_user).order_by('-created_at')
    context = {
        'profile_user': profile_user,
        'trips': trips,
        'trip_count': trips.count(),
    }
    return render(request, 'monitor_user.html', context)


def dashboard(request):
    if request.user.is_authenticated and request.user.is_staff:
        return redirect('monitor_dashboard')
        
    if request.user.is_authenticated:
        trips = Trip.objects.filter(user=request.user).order_by('-created_at')
    else:
        trips = Trip.objects.none()
    return render(request, 'dashboard.html', {'trips': trips})


def delete_trip(request, trip_id):
    if request.user.is_authenticated and request.user.is_staff:
        return redirect('monitor_dashboard')
        
    trip = get_object_or_404(Trip, id=trip_id)
    if trip.user == request.user or trip.user is None:
        trip.delete()
    return redirect('dashboard')


def login_view(request):
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')

        lock_key = f'login_lock_{username}'
        attempt_key = f'login_attempts_{username}'
        locked_until = cache.get(lock_key)

        if locked_until:
            remaining = int((locked_until - timezone.now()).total_seconds())
            return render(request, 'login.html', {
                'error': 'Too many failed attempts.',
                'locked': True,
                'remaining': max(remaining, 0),
                'username': username,
            })

        user = authenticate(request, username=username, password=password)

        if user is not None:
            cache.delete(attempt_key)
            cache.delete(lock_key)
            login(request, user)
            if user.is_staff:
                return redirect('monitor_dashboard')
            return redirect(request.GET.get('next', 'home'))
        else:
            attempts = cache.get(attempt_key, 0) + 1
            cache.set(attempt_key, attempts, LOCKOUT_SECONDS * 2)
            remaining_attempts = MAX_ATTEMPTS - attempts

            if attempts >= MAX_ATTEMPTS:
                locked_until = timezone.now() + datetime.timedelta(seconds=LOCKOUT_SECONDS)
                cache.set(lock_key, locked_until, LOCKOUT_SECONDS)
                cache.delete(attempt_key)
                return render(request, 'login.html', {
                    'error': 'Too many failed attempts.',
                    'locked': True,
                    'remaining': LOCKOUT_SECONDS,
                    'username': username,
                })

            return render(request, 'login.html', {
                'error': f'Invalid username or password. {remaining_attempts} attempt{"s" if remaining_attempts != 1 else ""} remaining.',
                'attempts_left': remaining_attempts,
                'username': username,
            })

    return render(request, 'login.html')


def send_magic_link(request):
    if request.method != 'POST':
        return redirect('login')

    username = request.POST.get('username', '').strip()

    # Rate-limit magic link requests per IP (max 5 in 5 minutes)
    ip = request.META.get('REMOTE_ADDR', 'unknown')
    magic_rate_key = f'magic_link_rate_{ip}'
    magic_attempts = cache.get(magic_rate_key, 0)
    if magic_attempts >= 5:
        return render(request, 'login.html', {
            'magic_sent': True,  # Silent — don't reveal rate limiting
            'username': username,
        })
    cache.set(magic_rate_key, magic_attempts + 1, 300)

    user = None
    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        # Use .filter().first() instead of .get() to avoid
        # MultipleObjectsReturned crash if two accounts share the same email
        user = User.objects.filter(email=username).first()

    if user and user.email:
        # Invalidate old tokens
        LoginToken.objects.filter(user=user, used=False).update(used=True)
        
        # Create new token
        token = LoginToken.objects.create(user=user)

        # Build the URL safely
        # reverse() finds the path: /magic-link/verify/<uuid>/
        relative_url = reverse('verify_magic_link', kwargs={'token': token.token})
        
        # Ensure SITE_URL doesn't have a trailing slash to avoid // in the URL
        base_url = settings.SITE_URL.rstrip('/')
        magic_url = f"{base_url}{relative_url}"

        try:
            html_message = render_to_string('emails/magic_link.html', {
                'user': user,
                'magic_url': magic_url,
                'site_url': base_url,
            })
            send_email(
                subject='🔐 Your Easytrip login link',
                to_email=user.email,
                html_content=html_message,
            )
        except Exception as e:
            print(f"[MAGIC LINK ERROR] {e}")

    return render(request, 'login.html', {
        'magic_sent': True,
        'username': username,
    })


def verify_magic_link(request, token):
    try:
        login_token = LoginToken.objects.get(token=token)
    except LoginToken.DoesNotExist:
        return render(request, 'login.html', {
            'error': 'This login link is invalid or has already been used.'
        })

    if not login_token.is_valid():
        return render(request, 'login.html', {
            'error': 'This login link has expired. Please request a new one.'
        })

    login_token.used = True
    login_token.save()

    user = login_token.user
    user.backend = 'django.contrib.auth.backends.ModelBackend'
    login(request, user)
    
    if user.is_staff:
        return redirect('monitor_dashboard')

    return redirect('home')


def logout_view(request):
    logout(request)
    return redirect('login')


def signup_view(request):
    if request.user.is_authenticated:
        return redirect('home')
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip().lower()
        password = request.POST.get('password', '')
        confirm_password = request.POST.get('confirm_password', '')

        # ── Honeypot check ──────────────────────────────────────────────────
        # The 'website' field is hidden from real users (CSS off-screen).
        # Bots crawl the HTML and fill every visible input — if it has a
        # value, this is almost certainly a bot. Silently redirect so the
        # bot thinks it worked (don't tell it why it failed).
        honeypot = request.POST.get('website', '')
        if honeypot:
            print(f"[BOT BLOCKED] Honeypot triggered from IP {request.META.get('REMOTE_ADDR')}")
            return redirect('login')   # silent — looks like success to the bot

        # ── Timing check ────────────────────────────────────────────────────
        # Bots fill forms in milliseconds. Real humans take at least 3 seconds.
        # form_load_time is stamped by JavaScript when the page loads.
        load_time = request.POST.get('form_load_time', '')
        if load_time:
            try:
                elapsed_seconds = (time.time() * 1000 - float(load_time)) / 1000
                if elapsed_seconds < 3:
                    print(f"[BOT BLOCKED] Form submitted in {elapsed_seconds:.2f}s from IP {request.META.get('REMOTE_ADDR')}")
                    return redirect('login')   # silent — looks like success to the bot
            except (ValueError, TypeError):
                pass   # If JS didn't stamp it (e.g. no-JS browser), let it through

        # ── Rate limiting: max 10 signup attempts per IP per 10 minutes ──
        ip = request.META.get('REMOTE_ADDR', 'unknown')
        rate_key = f'signup_rate_{ip}'
        attempts = cache.get(rate_key, 0)
        if attempts >= 10:
            return render(request, 'signup.html', {
                'error': 'Too many signup attempts from your network. Please wait a few minutes.',
                'username': username,
                'email': email,
            })
        cache.set(rate_key, attempts + 1, 600)  # 10-minute window

        # ── Basic input validation ──
        if not username or len(username) < 3:
            return render(request, 'signup.html', {
                'error': 'Username must be at least 3 characters long.',
                'email': email,
            })

        if not email:
            return render(request, 'signup.html', {
                'error': 'Email address is required to receive trip notifications.',
                'username': username,
            })

        if password != confirm_password:
            return render(request, 'signup.html', {
                'error': 'Passwords do not match.',
                'username': username,
                'email': email,
            })

        # ── Strong password validation ──
        pw_errors = []
        if len(password) < 8:
            pw_errors.append('at least 8 characters')
        if not re.search(r'[A-Z]', password):
            pw_errors.append('one uppercase letter')
        if not re.search(r'[a-z]', password):
            pw_errors.append('one lowercase letter')
        if not re.search(r'[0-9]', password):
            pw_errors.append('one number')
        if not re.search(r'[^A-Za-z0-9]', password):
            pw_errors.append('one special character')
        if pw_errors:
            return render(request, 'signup.html', {
                'error': 'Password must contain: ' + ', '.join(pw_errors) + '.',
                'username': username,
                'email': email,
            })

        # ── Pre-check duplicates before hitting the DB with create_user ──
        # These checks are NOT atomic (race condition possible in <1ms),
        # but the IntegrityError below is the true atomic safety net.
        if User.objects.filter(username=username).exists():
            return render(request, 'signup.html', {
                'error': 'Username is already taken. Please choose another.',
                'email': email,
            })

        if User.objects.filter(email=email).exists():
            return render(request, 'signup.html', {
                'error': 'An account with this email already exists. Try logging in instead.',
                'username': username,
            })

        try:
            user = User.objects.create_user(username=username, email=email, password=password)
            # Redirect to login instead of auto-logging in
            return redirect('login')

        except IntegrityError as e:
            # True atomic safety net — catches the rare simultaneous-signup race condition.
            # Inspect the error string to give a precise message.
            err_lower = str(e).lower()
            if 'email' in err_lower:
                error_msg = 'An account with this email already exists. Try logging in instead.'
            else:
                error_msg = 'Username is already taken. Please choose another.'
            return render(request, 'signup.html', {
                'error': error_msg,
                'username': username,
                'email': email,
            })

    return render(request, 'signup.html')