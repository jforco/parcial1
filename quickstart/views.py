from django.contrib.auth.models import Group, User
from rest_framework import  viewsets, status, generics
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from .models import *
from quickstart.serializers import *
from django.utils import timezone

class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]


class PermissionViewSet(viewsets.ReadOnlyModelViewSet): 
    queryset = Permission.objects.all()
    serializer_class = PermissionSerializer


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.filter(is_active=True).order_by('-date_joined')
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.is_active = False
        instance.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


class GroupViewSet(viewsets.ModelViewSet):
    queryset = Group.objects.all().order_by('name')
    serializer_class = GroupSerializer
    permission_classes = [IsAuthenticated]


class SoftDeleteModelViewSet(viewsets.ModelViewSet):
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()  # hace soft delete
        return Response(status=status.HTTP_204_NO_CONTENT)
    

class CategoriaViewSet(SoftDeleteModelViewSet):
    queryset = Categoria.objects.filter(eliminado=False)
    serializer_class = CategoriaSerializer
    permission_classes = [IsAuthenticated]


class ProductoViewSet(SoftDeleteModelViewSet):
    queryset = Producto.objects.filter(eliminado=False)
    serializer_class = ProductoSerializer
    permission_classes = [IsAuthenticated]


class SucursalViewSet(SoftDeleteModelViewSet):
    queryset = Sucursal.objects.filter(eliminado=False)
    serializer_class = SucursalSerializer
    permission_classes = [IsAuthenticated]


class InventariosViewSet(SoftDeleteModelViewSet):
    queryset = Inventario.objects.filter(eliminado=False)
    serializer_class = InventarioSerializer
    permission_classes = [IsAuthenticated]


class CarritoViewSet(viewsets.ModelViewSet):
    queryset = Carrito.objects.all()
    serializer_class = CarritoSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(id_usuario=self.request.user)


class DetalleCarritoViewSet(viewsets.ModelViewSet):
    queryset = DetalleCarrito.objects.all()
    serializer_class = DetalleCarritoSerializer
    permission_classes = [IsAuthenticated]


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def ultimo_carrito_usuario(request):
    carrito = Carrito.objects.filter(id_usuario=request.user).order_by('-fecha_creacion').first()

    if not carrito:
        carrito = Carrito.objects.create(
            id_usuario=request.user,
            fecha_creacion=timezone.now()
        )

    serializer = CarritoSerializer(carrito)
    return Response(serializer.data)