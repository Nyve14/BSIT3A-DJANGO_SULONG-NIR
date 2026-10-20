from django.urls import path

from . import views

app_name = 'transit'

urlpatterns = [
    path('', views.transit_home, name='home'),
    path('map/', views.transit_map, name='map'),
    path('routes/', views.route_list, name='route_list'),
    path('routes/new/', views.route_create, name='route_create'),
    path('routes/<int:pk>/', views.route_detail, name='route_detail'),
    path('routes/<int:pk>/edit/', views.route_edit, name='route_edit'),
    path('routes/<int:pk>/delete/', views.route_delete, name='route_delete'),
    path('routes/<int:route_pk>/stops/new/', views.stop_create, name='stop_create'),
    path('stops/<int:pk>/delete/', views.stop_delete, name='stop_delete'),
    path('routes/<int:route_pk>/schedules/new/', views.schedule_create, name='schedule_create'),
    path('schedules/<int:pk>/delete/', views.schedule_delete, name='schedule_delete'),
    path('schedules/', views.schedule_list, name='schedule_list'),
    path('stops/nearby/', views.stops_nearby, name='stops_nearby'),
    path('alerts/', views.alerts_list, name='alerts_list'),
    path('alerts/new/', views.alert_create, name='alert_create'),
    path('alerts/<int:pk>/delete/', views.alert_delete, name='alert_delete'),
    path('agencies/new/', views.agency_create, name='agency_create'),
]