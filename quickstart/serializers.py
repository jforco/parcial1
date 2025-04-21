from django.contrib.auth.models import Group, User, Permission
from rest_framework.serializers import ModelSerializer, HyperlinkedModelSerializer, SlugRelatedField, PrimaryKeyRelatedField
from .models import *

class RegisterSerializer(ModelSerializer):
    groups = SlugRelatedField(
        many=False,
        slug_field='name',
        queryset=Group.objects.all()
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'groups']
        extra_kwargs = {
            'password': {'write_only': True}
        }

    def create(self, validated_data):
        groups_data = validated_data.pop('groups', [])
        user = User.objects.create_user(**validated_data)
        user.groups.set(groups_data)
        return user
    

class PermissionSerializer(ModelSerializer):
    class Meta:
        model = Permission
        fields = ['id', 'codename', 'name', 'content_type']


class GroupSerializer(ModelSerializer):
    permissions = PermissionSerializer(many=True, read_only=True)
    permission_ids = PrimaryKeyRelatedField(
        queryset= Permission.objects.all(), many=True, write_only=True, source='permissions'
    )

    class Meta:
        model = Group
        fields = ['id', 'name', 'permissions', 'permission_ids']
    
    
class UserSerializer(HyperlinkedModelSerializer):
    groups = SlugRelatedField(
        many=False,
        slug_field='name',
        queryset=Group.objects.all()
    )
    class Meta:
        model = User
        fields = ['url', 'username', 'email', 'groups']


class GroupSerializer(HyperlinkedModelSerializer):
    class Meta:
        model = Group
        fields = ['url', 'name']

class CategoriaSerializer(ModelSerializer):
    class Meta:
        model = Categoria
        fields = ['id', 'nombre']

class ProductoSerializer(ModelSerializer):
    class Meta:
        model = Producto
        fields = ['id', 'categoria', 'nombre', 'tipo', 'medidas', 'precio', 'foto']

class SucursalSerializer(ModelSerializer):
    class Meta:
        model = Sucursal
        fields = ['id', 'nombre', 'direccion']

class InventarioSerializer(ModelSerializer):
    class Meta:
        model = Inventario
        fields = ['id', 'producto', 'sucursal', 'cantidad']