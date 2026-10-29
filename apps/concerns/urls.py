from django.urls import path

from . import views

app_name = 'reports'

urlpatterns = [
    path('', views.concern_list, name='list'),
    path('new/', views.concern_create, name='create'),
    path('api/areas/', views.api_get_child_areas, name='api_areas'),
    path('<uuid:reference>/updates/', views.concern_updates, name='updates'),
    path('<uuid:reference>/update/', views.concern_update, name='update'),
    path('<uuid:reference>/delete/', views.concern_delete, name='delete'),
    path('<uuid:reference>/', views.concern_detail, name='detail'),
]
