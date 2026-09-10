from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
import uuid

class Bodega(models.Model):
    """Modelo para las bodegas/almacenes"""
    nombre = models.CharField(max_length=100, unique=True)
    ubicacion = models.CharField(max_length=200, blank=True)
    descripcion = models.TextField(blank=True)
    activa = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.nombre

    class Meta:
        verbose_name = 'Bodega'
        verbose_name_plural = 'Bodegas'
        ordering = ['nombre']

class Categoria(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    descripcion = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nombre

    class Meta:
        verbose_name = 'Categoría'
        verbose_name_plural = 'Categorías'
        ordering = ['nombre']

class Producto(models.Model):
    nombre = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True)
    categoria = models.ForeignKey(Categoria, on_delete=models.SET_NULL, null=True, blank=True)
    precio = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    precio_costo = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    codigo = models.CharField(max_length=50, unique=True)
    stock_minimo = models.PositiveIntegerField(default=5)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.nombre} ({self.codigo})"

    class Meta:
        verbose_name = 'Producto'
        verbose_name_plural = 'Productos'
        ordering = ['nombre']

class Inventario(models.Model):
    """Stock por producto y bodega"""
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    bodega = models.ForeignKey(Bodega, on_delete=models.CASCADE)
    cantidad = models.PositiveIntegerField(default=0)
    stock_minimo = models.PositiveIntegerField(default=5)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['producto', 'bodega']
        verbose_name = 'Inventario'
        verbose_name_plural = 'Inventarios'
        ordering = ['bodega', 'producto__nombre']

    def __str__(self):
        return f"{self.producto.nombre} - {self.bodega.nombre}: {self.cantidad}"

class Movimiento(models.Model):
    TIPO_ENTRADA = 'ENT'
    TIPO_SALIDA = 'SAL'
    TIPO_TRASLADO = 'TRA'
    
    TIPO_CHOICES = [
        (TIPO_ENTRADA, 'Entrada'),
        (TIPO_SALIDA, 'Salida'),
        (TIPO_TRASLADO, 'Traslado'),
    ]
    
    tipo = models.CharField(max_length=3, choices=TIPO_CHOICES)
    numero_boleta = models.CharField(max_length=50, unique=True, blank=True)
    numero_adendum = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name='Número de Adendum',
        help_text='Número del adendum que justifica el movimiento'
    )
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    bodega_origen = models.ForeignKey(Bodega, on_delete=models.CASCADE, related_name='movimientos_origen', null=True, blank=True)
    bodega_destino = models.ForeignKey(Bodega, on_delete=models.CASCADE, related_name='movimientos_destino', null=True, blank=True)
    cantidad = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    descripcion = models.TextField(blank=True)
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def save(self, *args, **kwargs):
        if not self.numero_boleta:
            self.numero_boleta = self._generar_numero_boleta()
        super().save(*args, **kwargs)
    
    def _generar_numero_boleta(self):
        """Genera un número de boleta único con formato BOL-YYYYMMDD-XXXX"""
        import datetime
        
        hoy = datetime.datetime.now().strftime('%Y%m%d')
        prefijo = f"BOL-{hoy}-"
        
        # Buscar el último número de boleta del día
        ultimo = Movimiento.objects.filter(
            numero_boleta__startswith=prefijo
        ).order_by('-numero_boleta').first()
        
        if ultimo:
            # Extraer el número secuencial (últimos 4 dígitos)
            try:
                ultimo_numero = int(ultimo.numero_boleta.split('-')[-1])
                nuevo_numero = ultimo_numero + 1
            except (ValueError, IndexError):
                nuevo_numero = 1
        else:
            nuevo_numero = 1
        
        # Generar nuevo número de boleta
        numero_boleta = f"{prefijo}{nuevo_numero:04d}"
        
        # Verificar que no exista (por si acaso)
        while Movimiento.objects.filter(numero_boleta=numero_boleta).exists():
            nuevo_numero += 1
            numero_boleta = f"{prefijo}{nuevo_numero:04d}"
        
        return numero_boleta
    
    def __str__(self):
        return f"{self.get_tipo_display()} - {self.numero_boleta} - {self.producto.nombre}"
    
    class Meta:
        verbose_name = 'Movimiento'
        verbose_name_plural = 'Movimientos'
        ordering = ['-created_at']
    
    class Meta:
        verbose_name = 'Movimiento'
        verbose_name_plural = 'Movimientos'
        ordering = ['-created_at']