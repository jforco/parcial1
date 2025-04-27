from django.contrib.auth.models import Group, User
from rest_framework import  viewsets, status, generics
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework_simplejwt.views import TokenObtainPairView
from .models import *
from quickstart.serializers import *
from django.utils import timezone
from django.db.models import F, Sum, DecimalField, ExpressionWrapper, Prefetch
from decimal import Decimal, ROUND_HALF_UP

from django.http import HttpResponse
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
import stripe
stripe.api_key = settings.STRIPE_SECRET_KEY

class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)

        if serializer.is_valid():
            user = serializer.save()

            # Ahora usamos el CustomTokenObtainPairSerializer para generar misma respuesta que login
            token_serializer = CustomTokenObtainPairSerializer(data={
                'username': request.data['username'],
                'password': request.data['password']
            }, context={'request': request} )

            if token_serializer.is_valid():
                return Response(token_serializer.validated_data, status=status.HTTP_201_CREATED)
            else:
                return Response(token_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer


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
    
    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [AllowAny()]
        return [IsAuthenticated()]

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return ProductoDetailSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return ProductoCreateUpdateSerializer
        return ProductoListSerializer


class SucursalViewSet(SoftDeleteModelViewSet):
    queryset = Sucursal.objects.filter(eliminado=False)
    serializer_class = SucursalSerializer
    permission_classes = [IsAuthenticated]


class InventariosViewSet(SoftDeleteModelViewSet):
    queryset = Inventario.objects.filter(eliminado=False)
    serializer_class = InventarioSerializer
    permission_classes = [IsAuthenticated]


class CarritoViewSet(viewsets.ModelViewSet):
    queryset = Carrito.objects.filter(eliminado=False).prefetch_related(
        Prefetch('detalles', queryset=DetalleCarrito.objects.filter(eliminado=False))
    )
    serializer_class = CarritoSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(id_usuario=self.request.user)


class DetalleCarritoViewSet(viewsets.ModelViewSet):
    queryset = DetalleCarrito.objects.filter(eliminado=False)
    serializer_class = DetalleCarritoSerializer
    permission_classes = [IsAuthenticated]


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def ultimo_carrito_usuario(request):
    carrito = Carrito.objects.filter(id_usuario=request.user, eliminado=False).order_by('-fecha_creacion').first()

    if not carrito:
        carrito = Carrito.objects.create(
            id_usuario=request.user,
            fecha_creacion=timezone.now()
        )

    serializer = CarritoSerializer(carrito)
    return Response(serializer.data)


class PedidoViewSet(viewsets.ModelViewSet):
    queryset = Pedido.objects.all()
    serializer_class = PedidoSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Pedido.objects.filter(id_usuario=self.request.user)

    def get_object(self):
        return Pedido.objects.get(pk=self.kwargs['pk'])

    def create(self, request, *args, **kwargs):
        return Response({'detail': 'Creación de pedidos no permitida por este endpoint.'}, status=status.HTTP_403_FORBIDDEN)

    def destroy(self, request, *args, **kwargs):
        return Response({'detail': 'Eliminación de pedidos no permitida por este endpoint.'}, status=status.HTTP_403_FORBIDDEN)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        nuevo_estado = request.data.get('estado')
        if nuevo_estado and nuevo_estado in dict(instance.ESTADOS):
            instance.estado = nuevo_estado
            instance.save()
            serializer = self.get_serializer(instance)
            return Response(serializer.data)
        return Response({'detail': 'Solo se permite modificar el estado.'}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'], url_path='todos')
    def listar_todos(self, request):
        pedidos = Pedido.objects.all()
        serializer = self.get_serializer(pedidos, many=True)
        return Response(serializer.data)
    

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def iniciar_pago(request):
    id_carrito = request.data.get('id_carrito')
    carrito = Carrito.objects.filter(id=id_carrito, id_usuario=request.user, eliminado=False).first()
    
    if not carrito:
        return Response({'error': 'Carrito no válido'}, status=400)

    # Crear pedido pendiente
    items_carrito = DetalleCarrito.objects.filter(id_carrito=id_carrito, eliminado=False).select_related('id_producto')
    if not items_carrito.exists():
        return Response({'error': 'El carrito está vacío, no se puede crear el pedido.'}, status=400)

    total_carrito = sum(item.cantidad * item.id_producto.precio for item in items_carrito)
    total_carrito = Decimal(total_carrito).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    if total_carrito == 0:
        return Response({'error': 'El carrito está vacío o con items que no tienen valor.'}, status=400);

    # crear pedido y detalles
    pedido = Pedido.objects.create(
        id_usuario=request.user,
        id_carrito=carrito,
        monto_total=total_carrito,
        direccion_entrega=request.data.get('direccion'),
        estado="pendiente",
        latitud=request.data.get('latitud'),
        longitud=request.data.get('longitud')
    )

    detalles_pedido = [
        DetallePedido(
            id_pedido=pedido,
            id_producto=item.id_producto,
            cantidad=item.cantidad,
            precio=item.id_producto.precio,
            precio_total=item.id_producto.precio * item.cantidad
        )
        for item in items_carrito
    ]
    DetallePedido.objects.bulk_create(detalles_pedido)
    '''for item in DetalleCarrito.objects.filter(id_carrito=id_carrito): 
        DetallePedido.objects.create(
            id_pedido=pedido,
            id_producto=item.id_producto,
            cantidad=item.cantidad,
            precio=item.id_producto.precio,
            precio_total=item.id_producto.precio * item.cantidad
        )'''

    # Crear Stripe Checkout Session
    #tasa_cambio = Decimal('6.97')
    #cobro_dolar = (total_carrito / tasa_cambio).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    
    urlFrontBase = request.data.get('url_front_base')

    session = stripe.checkout.Session.create(
        payment_method_types=['card'],
        mode='payment',
        line_items=[{
            'price_data': {
                'currency': 'bob',
                'product_data': {
                    'name': 'Pedido #{}'.format(pedido.id),
                },
                'unit_amount': int(total_carrito * 100),
            },
            'quantity': 1,
        }],
        metadata={
            'pedido_id': pedido.id
        },
        success_url=urlFrontBase + '/success',
        cancel_url=urlFrontBase + '/cancel',
    )

    return Response({'sessionId': session.id})


@csrf_exempt
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    event = None

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except (ValueError, stripe.error.SignatureVerificationError) as e:
        return HttpResponse(status=400)

    if event['type'] not in ['checkout.session.completed', 'checkout.session.expired']:
        return HttpResponse(status=200)

    session = event['data']['object']
    pedido_id = session['metadata']['pedido_id']

    try:
        pedido = Pedido.objects.get(id=pedido_id)
    except Pedido.DoesNotExist:
        return HttpResponse(status=404)

    if event['type'] == 'checkout.session.completed':
        pedido.estado = 'confirmado'
        pedido.save()

        if pedido.id_carrito:
            carrito = pedido.id_carrito
            if not carrito.eliminado:
                carrito.delete()
                nuevo_carrito = Carrito.objects.create(id_usuario=pedido.id_usuario, fecha_creacion=timezone.now())

    elif event['type'] == 'checkout.session.expired':
        pedido.estado = 'cancelado'
        pedido.save()

    return HttpResponse(status=200)