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
    

