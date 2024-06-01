from django.urls import path

from .consumers import WebRunnerConsumer

websocket_urlpatterns = [path('ws/webrunner/', WebRunnerConsumer)]
