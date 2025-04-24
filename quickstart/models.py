from django.db import models
from django.contrib.auth.models import User

class SoftDeleteModel(models.Model):
    eliminado = models.BooleanField(default=False)

    def delete(self, using=None, keep_parents=False):
        self.eliminado = True
        self.save()

    class Meta:
        abstract = True


class Categoria(SoftDeleteModel):
    nombre = models.CharField(max_length=50)
    descripcion = models.CharField(max_length=100, null=True)

    def __str__(self):
        return self.nombre
    

class Producto(SoftDeleteModel):
    categoria = models.ForeignKey('Categoria', on_delete=models.CASCADE, related_name='productos')
    nombre = models.CharField(max_length=100)
    tipo = models.CharField(max_length=50, null=True)
    medidas = models.CharField(max_length=100, null=True)
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    foto = models.ImageField(upload_to='productos/', null=True, blank=True)

    sucursales = models.ManyToManyField('Sucursal', through='Inventario', related_name='productos')

    def __str__(self):
        return self.nombre


class Sucursal(SoftDeleteModel):
    nombre = models.CharField(max_length=50)
    direccion = models.CharField(max_length=100, null=True)

    def __str__(self):
        return self.nombre
    
    
class Inventario(SoftDeleteModel):
    producto = models.ForeignKey('Producto', on_delete=models.CASCADE)
    sucursal = models.ForeignKey('Sucursal', on_delete=models.CASCADE)
    cantidad = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ('producto', 'sucursal')

    def __str__(self):
        return f"{self.producto.nombre} en {self.sucursal.nombre}: {self.cantidad}"
    

class Carrito(SoftDeleteModel):
    id = models.AutoField(primary_key=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    id_usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='carritos')

    def __str__(self):
        return f'Carrito {self.id} de {self.id_usuario.username}'


class DetalleCarrito(SoftDeleteModel):
    id = models.AutoField(primary_key=True)
    id_carrito = models.ForeignKey(Carrito, on_delete=models.CASCADE, related_name='detalles')
    id_producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    cantidad = models.PositiveIntegerField()

    def __str__(self):
        return f'{self.cantidad}x {self.id_producto.nombre} en carrito {self.id_carrito.id}'
    

class Pedido(models.Model):
    ESTADOS = (
        ('pendiente', 'Pendiente'),
        ('confirmado', 'Confirmado'),
        ('enviado', 'Enviado'),
        ('entregado', 'Entregado'),
        ('cancelado', 'Cancelado'),
    )

    id_usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='pedidos')
    id_carrito = models.ForeignKey(Carrito, on_delete=models.SET_NULL, null=True, blank=True)
    monto_total = models.DecimalField(max_digits=10, decimal_places=2)
    direccion_entrega = models.CharField(max_length=255)
    latitud = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitud = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    estado = models.CharField(max_length=20, choices=ESTADOS, default='pendiente')
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Pedido #{self.pk} - {self.estado}"
    

class DetallePedido(models.Model):
    id_pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, related_name='detalles')
    id_producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    cantidad = models.PositiveIntegerField()
    precio = models.DecimalField(max_digits=10, decimal_places=2)  # Precio unitario
    precio_total = models.DecimalField(max_digits=10, decimal_places=2)  # cantidad * precio
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Detalle del Pedido {self.id_pedido_id} - Producto {self.id_producto_id}"
    

    
