from django.urls import path
from . import views

urlpatterns = [
    path('', views.login_view, name='login'),
    path('home/', views.home, name='dashboard'),
    path('map/', views.interactive_map, name='interactive_map'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register_view, name='register'),
]