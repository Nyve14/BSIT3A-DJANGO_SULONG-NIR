from django.urls import path

from . import views

app_name = 'alerts'

urlpatterns = [
    path('', views.alert_list, name='list'),
    path('new/', views.alert_create, name='create'),
    path('<int:pk>/', views.alert_detail, name='detail'),
    path('<int:pk>/send/', views.alert_send, name='send'),
    path('delivery/<int:pk>/read/', views.alert_mark_read, name='mark_read'),
    path('my/', views.user_alerts, name='my_alerts'),
    path('preferences/', views.user_preferences, name='user_preferences'),
    path('api/count/', views.alert_count, name='api_count'),
]