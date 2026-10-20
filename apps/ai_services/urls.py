from django.urls import path

from . import views

app_name = 'ai_services'

urlpatterns = [
    path('', views.ai_dashboard, name='dashboard'),
    path('api/classify/', views.api_classify_report, name='api_classify'),
    path('api/duplicates/', views.api_find_duplicates, name='api_duplicates'),
    path('api/suggest-response/', views.api_suggest_response, name='api_suggest_response'),
]