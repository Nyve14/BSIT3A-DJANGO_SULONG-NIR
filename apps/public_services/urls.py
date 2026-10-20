from django.urls import path

from . import views

app_name = 'public_services'

urlpatterns = [
    path('', views.service_list, name='list'),
    path('map/', views.service_map, name='map'),
    path('new/', views.service_create, name='create'),
    path('category/<slug:category_slug>/', views.service_category, name='category'),
    path('<slug:slug>/', views.service_detail, name='detail'),
    path('<slug:slug>/edit/', views.service_edit, name='edit'),
    path('<slug:slug>/delete/', views.service_delete, name='delete'),
    path('<slug:slug>/review/', views.service_add_review, name='add_review'),
]