from django.contrib.auth.models import Group, User
from rest_framework import  viewsets, status, generics
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from .models import *
from quickstart.serializers import *
from django.utils import timezone
from django.db.models import F, Sum, DecimalField, ExpressionWrapper
from decimal import Decimal, ROUND_HALF_UP
import stripe
from django.http import HttpResponse
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt

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


class PedidoViewSet(viewsets.ModelViewSet):
    queryset = Pedido.objects.all()
    serializer_class = PedidoSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Pedido.objects.filter(id_usuario=self.request.user)

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
    

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def iniciar_pago(request):
    id_carrito = request.data.get('id_carrito')
    carrito = Carrito.objects.filter(id=id_carrito, id_usuario=request.user, eliminado=False).first()
    
    if not carrito:
        return Response({'error': 'Carrito no válido'}, status=400)

    # Crear pedido pendiente
    total_carrito = DetalleCarrito.objects.filter(id_carrito=id_carrito).annotate(
        subtotal=ExpressionWrapper(
            F('cantidad') * F('id_producto__precio'),
            output_field=DecimalField(max_digits=12, decimal_places=2)
        )
    ).aggregate(total=Sum('subtotal'))['total'] or 0
    total_carrito = total_carrito.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    pedido = Pedido.objects.create(
        id_usuario=request.user,
        id_carrito=carrito,
        monto_total=total_carrito,
        direccion_entrega=request.data.get('direccion'),
        estado="pendiente",
        latitud=request.data.get('latitud'),
        longitud=request.data.get('longitud')
    )

    # Crear detalles
    for item in carrito.items.all():  # ajustá según tus relaciones
        DetallePedido.objects.create(
            id_pedido=pedido,
            id_producto=item.producto,
            cantidad=item.cantidad,
            precio=item.producto.precio,
            precio_total=item.producto.precio * item.cantidad
        )

    # Crear Stripe Checkout Session
    tasa_cambio = Decimal('6.97')
    cobro_dolar = (total_carrito / tasa_cambio).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    
    session = stripe.checkout.Session.create(
        payment_method_types=['card'],
        mode='payment',
        line_items=[{
            'price_data': {
                'currency': 'usd',
                'product_data': {
                    'name': 'Pedido #{}'.format(pedido.id),
                },
                'unit_amount': int(cobro_dolar * 100),
            },
            'quantity': 1,
        }],
        metadata={
            'pedido_id': pedido.id
        },
        success_url='http://localhost:3000/success',
        cancel_url='http://localhost:3000/cancel',
    )

    return Response({'sessionId': session.id})


@csrf_exempt
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META['HTTP_STRIPE_SIGNATURE']
    event = None

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError:
        return HttpResponse(status=400)

    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        pedido_id = session['metadata']['pedido_id']
        Pedido.objects.filter(id=pedido_id).update(estado='confirmado')

    elif event['type'] == 'checkout.session.expired':
        session = event['data']['object']
        pedido_id = session['metadata']['pedido_id']
        Pedido.objects.filter(id=pedido_id).update(estado='cancelado')

    return HttpResponse(status=200)