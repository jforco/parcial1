from django.contrib.auth.models import Group, User, Permission
from rest_framework.serializers import ModelSerializer, HyperlinkedModelSerializer, SlugRelatedField, PrimaryKeyRelatedField, SerializerMethodField, CharField, DecimalField
from .models import *
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        # Agrega datos del usuario
        data['user'] = UserSerializer(self.user, context=self.context).data
        return data
    

class RegisterSerializer(ModelSerializer):
    groups = SlugRelatedField(
        many=True,
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
        print('Datos validados:', validated_data)
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
        many=True,
        slug_field='name',
        queryset=Group.objects.all(),
        required=False
    )
    class Meta:
        model = User
        fields = ['url', 'username', 'email', 'groups']


class CategoriaSerializer(ModelSerializer):
    class Meta:
        model = Categoria
        fields = ['id', 'nombre', 'descripcion']


class ProductoSerializer(ModelSerializer):
    inventario = SerializerMethodField()

    class Meta:
        model = Producto
        fields = ['id', 'categoria', 'nombre', 'tipo', 'medidas', 'precio', 'foto', 'inventario']

    def get_inventario(self, obj):
        inventarios = Inventario.objects.filter(producto=obj, eliminado=False)  # si usás soft delete
        return InventarioSerializer(inventarios, many=True).data


class SucursalSerializer(ModelSerializer):
    class Meta:
        model = Sucursal
        fields = ['id', 'nombre', 'direccion']


class InventarioSerializer(ModelSerializer):
    sucursal = PrimaryKeyRelatedField(queryset=Sucursal.objects.all())
    producto = PrimaryKeyRelatedField(queryset=Producto.objects.all())
    sucursal_detalle = SucursalSerializer(source='sucursal', read_only=True)
    class Meta:
        model = Inventario
        fields = ['id', 'producto', 'sucursal', 'sucursal_detalle', 'cantidad']


class ProductoSimpleSerializer(ModelSerializer):
    class Meta:
        model = Producto
        fields = ['id', 'nombre', 'precio'] 


class DetalleCarritoSerializer(ModelSerializer):
    id_producto = PrimaryKeyRelatedField(queryset=Producto.objects.all())
    producto_nombre = CharField(source='id_producto.nombre', read_only=True)
    producto_precio = DecimalField(source='id_producto.precio', max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = DetalleCarrito
        fields = ['id', 'id_carrito', 'id_producto', 'producto_nombre', 'producto_precio', 'cantidad']

    def create(self, validated_data):
        carrito = validated_data['id_carrito']
        producto = validated_data['id_producto']
        cantidad_nueva = validated_data['cantidad']

        # Verificamos si ya existe un detalle para el mismo carrito y producto
        detalle_existente = DetalleCarrito.objects.filter(
            id_carrito=carrito,
            id_producto=producto,
            eliminado=False
        ).first()

        if detalle_existente:
            detalle_existente.cantidad += cantidad_nueva
            detalle_existente.save()
            return detalle_existente

        # Si no existe, se crea como nuevo
        return super().create(validated_data)



class CarritoSerializer(ModelSerializer):
    detalles = DetalleCarritoSerializer(many=True, read_only=True)

    class Meta:
        model = Carrito
        fields = ['id', 'fecha_creacion', 'id_usuario', 'detalles']


class DetallePedidoSerializer(ModelSerializer):
    class Meta:
        model = DetallePedido
        fields = ['id', 'id_producto', 'cantidad', 'precio', 'precio_total', 'fecha_creacion']


class PedidoSerializer(ModelSerializer):
    detalles = DetallePedidoSerializer(many=True, read_only=True)

    class Meta:
        model = Pedido
        fields = ['id', 'id_carrito', 'id_usuario', 'monto_total', 'direccion_entrega',
                  'latitud', 'longitud', 'estado', 'fecha_creacion', 'fecha_modificacion', 'detalles']
        read_only_fields = ['id_usuario', 'fecha_creacion', 'fecha_modificacion', 'detalles']