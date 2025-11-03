from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('api/monitoring/', views.proxy_monitoring, name='proxy_monitoring'),
    path('api/speed/', views.proxy_speed, name='proxy_speed'),
]