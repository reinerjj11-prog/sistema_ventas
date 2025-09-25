from django.db import models
from django.contrib.auth.models import User
from clientes.models import Cliente   # importamos el modelo de la nueva app


class Producto(models.Model):
    nombre = models.CharField(max_length=100)
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.PositiveIntegerField()
    categoria = models.CharField(max_length=50, blank=True, null=True)
    imagen = models.ImageField(upload_to='productos/', null=True, blank=True)
    
    def __str__(self):
        return self.nombre


class Venta(models.Model):
    fecha = models.DateTimeField(auto_now_add=True)
    cliente = models.ForeignKey(Cliente, on_delete=models.SET_NULL, null=True, blank=True, related_name='ventas')
    vendedor = models.ForeignKey(User, on_delete=models.CASCADE)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    def __str__(self):
        return f"Venta #{self.id} - {self.fecha.strftime('%Y-%m-%d %H:%M')}"


class DetalleVenta(models.Model):
    venta = models.ForeignKey(Venta, on_delete=models.CASCADE, related_name='detalles')
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    cantidad = models.PositiveIntegerField()
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)

    def save(self, *args, **kwargs):
        self.subtotal = self.cantidad * self.producto.precio
        super().save(*args, **kwargs)
        self.producto.stock -= self.cantidad
        self.producto.save()

    def __str__(self):
        return f"{self.cantidad} x {self.producto.nombre}"
