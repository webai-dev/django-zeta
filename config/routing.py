from django.conf.urls import url

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter

# XXX: Address in issue #503
# from graphql_ws.django_channels import GraphQLSubscriptionConsumer

from ery_backend.base.routing import websocket_urlpatterns

application = ProtocolTypeRouter(
    {
        # (http->django views is added by default)
        'websocket': AuthMiddlewareStack(URLRouter(websocket_urlpatterns)),
    }
)
# XXX: Address in issue #503
# Alex's code
#    'websocket': AuthMiddlewareStack(
#        URLRouter([
#            url(r'^/subscriptions', GraphQLSubscriptionConsumer),
#             ery_backend.hands.routing.websocket_urlpatterns
#        ])
#    ),
