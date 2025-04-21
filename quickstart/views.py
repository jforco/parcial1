from django.contrib.auth.models import Group, User
from rest_framework import permissions, viewsets, status, generics
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from .models import *
from quickstart.serializers import *

class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]


class PermissionViewSet(viewsets.ReadOnlyModelViewSet): 
    queryset = Permission.objects.all()
    serializer_class = PermissionSerializer


class UserViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows users to be viewed or edited.
    """
    queryset = User.objects.all().order_by('-date_joined')
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.is_active = False
        instance.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


class GroupViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows groups to be viewed or edited.
    """
    queryset = Group.objects.all().order_by('name')
    serializer_class = GroupSerializer
    permission_classes = [permissions.IsAuthenticated]


class SoftDeleteModelViewSet(viewsets.ModelViewSet):
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()  # hace soft delete
        return Response(status=status.HTTP_204_NO_CONTENT)
    

class CategoriaViewSet(SoftDeleteModelViewSet):
    queryset = Categoria.objects.filter(eliminado=False)
    serializer_class = CategoriaSerializer
    permission_classes = [permissions.IsAuthenticated]


class ProductoViewSet(SoftDeleteModelViewSet):
    queryset = Producto.objects.filter(eliminado=False)
    serializer_class = ProductoSerializer
    permission_classes = [permissions.IsAuthenticated]


class SucursalViewSet(SoftDeleteModelViewSet):
    queryset = Sucursal.objects.filter(eliminado=False)
    serializer_class = SucursalSerializer
    permission_classes = [permissions.IsAuthenticated]


class InventariosViewSet(SoftDeleteModelViewSet):
    queryset = Inventario.objects.filter(eliminado=False)
    serializer_class = InventarioSerializer
    permission_classes = [permissions.IsAuthenticated]