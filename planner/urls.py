from django.urls import path, include
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('trip/<int:trip_id>/', views.trip_detail, name='trip_detail'),
    path('trip/<int:trip_id>/delete/', views.delete_trip, name='delete_trip'),
    path('login/', views.login_view, name='login'),
    path('signup/', views.signup_view, name='signup'),
    path('logout/', views.logout_view, name='logout'),
    path('api/spots/', views.spots_by_category, name='spots_by_category'),
    path('trips/<int:trip_id>/generate-itinerary/', views.generate_itinerary, name='generate_itinerary'),
    path('magic-link/send/', views.send_magic_link, name='send_magic_link'),
    path('magic-link/verify/<uuid:token>/', views.verify_magic_link, name='verify_magic_link'),
    path('monitor/', views.monitor_dashboard, name='monitor_dashboard'),
    path('monitor/user/<int:user_id>/', views.monitor_user_detail, name='monitor_user_detail'),
    
]