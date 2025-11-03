from django.urls import path
from . import consumers

websocket_urlpatterns = [
    path('ws/vehicle_data/', consumers.VehicleDataConsumer.as_asgi()),
]