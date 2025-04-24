"""
URL configuration for parcial1 project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.urls import include, path
from rest_framework import routers
from django.conf import settings
from django.conf.urls.static import static
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenBlacklistView
)

from quickstart.views import *

router = routers.DefaultRouter()
router.register(r'permissions', PermissionViewSet)
router.register(r'users', UserViewSet)
router.register(r'groups', GroupViewSet)
router.register(r'categorias', CategoriaViewSet)
router.register(r'productos', ProductoViewSet)
router.register(r'sucursales', SucursalViewSet)
router.register(r'inventarios', InventariosViewSet)
router.register(r'carritos', CarritoViewSet)
router.register(r'detalles_carrito', DetalleCarritoViewSet)
router.register(r'pedidos', PedidoViewSet)

# Wire up our API using automatic URL routing.
# Additionally, we include login URLs for the browsable API.
urlpatterns = [
    path('api/', include(router.urls)),
    path('api-auth/', include('rest_framework.urls', namespace='rest_framework'))
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

urlpatterns += [
    path('api/token', TokenObtainPairView.as_view(), name='token_obtain_pair'),  # login
    path('api/token/refresh', TokenRefreshView.as_view(), name='token_refresh'),  # refresh
    path('api/token/logout', TokenBlacklistView.as_view(), name='token_blacklist'),  # logout
    path('api/register', RegisterView.as_view(), name='register'),
]

#vistas personalizadas
urlpatterns += [ 
    path('api/ultimo_carrito/', ultimo_carrito_usuario),
    path('api/pagar/', iniciar_pago),
    path('api/stripe/webhook/', stripe_webhook),
]