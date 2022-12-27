from django.urls import path

from .consumers import BattleConsumer

websocket_urlpatterns = [
    path('ws/battle/<str:address>/', BattleConsumer.as_asgi())
]
