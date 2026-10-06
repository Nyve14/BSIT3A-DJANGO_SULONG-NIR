from django.urls import path

from . import views

app_name = 'service_requests'

urlpatterns = [
    path('', views.request_list, name='list'),
    path('new/', views.request_create, name='create'),
    path('<uuid:reference>/update/', views.request_update, name='update'),
    path('<uuid:reference>/', views.request_detail, name='detail'),
]
