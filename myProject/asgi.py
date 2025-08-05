import os
from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application
import myApp.routing  # <-- import your routing

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myProject.settings')

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": URLRouter(myApp.routing.websocket_urlpatterns),
})
