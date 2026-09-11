from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator


# ============================================================
# BODEGA
# ============================================================

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


# ============================================================
# CATEGORÍA
# ============================================================

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


# ============================================================
# PRODUCTO (modelo genérico)
# ============================================================

class Producto(models.Model):
    nombre = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True)
    categoria = models.ForeignKey(Categoria, on_delete=models.SET_NULL, null=True, blank=True)
    precio = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    precio_costo = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    codigo = models.CharField(max_length=50, unique=True)
    stock_minimo = models.PositiveIntegerField(default=5)
    
    # NUEVO: indica si el producto maneja número de serie único por unidad
    maneja_serie = models.BooleanField(
        default=False,
        verbose_name='¿Maneja número de serie?',
        help_text='Marcar si cada unidad física tiene un número de serie único'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.nombre} ({self.codigo})"

    @property
    def stock_total(self):
        """Suma total del stock en todas las bodegas"""
        return self.inventarios.aggregate(total=models.Sum('cantidad'))['total'] or 0

    class Meta:
        verbose_name = 'Producto'
        verbose_name_plural = 'Productos'
        ordering = ['nombre']


# ============================================================
# UNIDAD (instancia física con número de serie)
# ============================================================

class Unidad(models.Model):
    """Instancia física de un producto que maneja número de serie"""
    ESTADO_DISPONIBLE = 'disponible'
    ESTADO_VENDIDO = 'vendido'
    ESTADO_DAÑADO = 'dañado'
    ESTADO_RESERVADO = 'reservado'
    
    ESTADO_CHOICES = [
        (ESTADO_DISPONIBLE, 'Disponible'),
        (ESTADO_VENDIDO, 'Vendido'),
        (ESTADO_DAÑADO, 'Dañado'),
        (ESTADO_RESERVADO, 'Reservado'),
    ]
    
    producto = models.ForeignKey(
        Producto,
        on_delete=models.CASCADE,
        related_name='unidades'
    )
    numero_serie = models.CharField(
        max_length=100,
        unique=True,
        verbose_name='Número de Serie'
    )
    bodega = models.ForeignKey(
        Bodega,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='unidades'
    )
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default=ESTADO_DISPONIBLE
    )
    notas = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.producto.codigo} - {self.numero_serie}"

    class Meta:
        verbose_name = 'Unidad'
        verbose_name_plural = 'Unidades'
        ordering = ['producto', 'numero_serie']


# ============================================================
# INVENTARIO (stock agregado por producto y bodega)
# ============================================================

class Inventario(models.Model):
    """Stock por producto y bodega (para productos sin serie o como resumen)"""
    producto = models.ForeignKey(
        Producto,
        on_delete=models.CASCADE,
        related_name='inventarios'  # ← necesario para stock_total
    )
    bodega = models.ForeignKey(Bodega, on_delete=models.CASCADE, related_name='inventarios')
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


# ============================================================
# MOVIMIENTO MASIVO (debe ir ANTES de Movimiento)
# ============================================================

class MovimientoMasivo(models.Model):
    """Agrupa varios movimientos bajo una misma boleta"""
    TIPO_ENTRADA = 'ENT'
    TIPO_SALIDA = 'SAL'
    TIPO_TRASLADO = 'TRA'

    TIPO_CHOICES = [
        (TIPO_ENTRADA, 'Entrada Masiva'),
        (TIPO_SALIDA, 'Salida Masiva'),
        (TIPO_TRASLADO, 'Traslado Masivo'),
    ]

    tipo = models.CharField(max_length=3, choices=TIPO_CHOICES)
    numero_boleta = models.CharField(max_length=50, unique=True, blank=True)
    numero_adendum = models.CharField(max_length=50, blank=True, null=True)
    bodega = models.ForeignKey(
        Bodega,
        on_delete=models.CASCADE,
        related_name='movimientos_masivos_principal'
    )
    bodega_destino = models.ForeignKey(
        Bodega,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='movimientos_masivos_destino'
    )
    descripcion = models.TextField(blank=True)
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.numero_boleta:
            self.numero_boleta = self._generar_numero_boleta()
        super().save(*args, **kwargs)

    def _generar_numero_boleta(self):
        import datetime
        hoy = datetime.datetime.now().strftime('%Y%m%d')
        prefijos = {
            self.TIPO_ENTRADA: 'MAS-E',
            self.TIPO_SALIDA: 'MAS-S',
            self.TIPO_TRASLADO: 'MAS-T',
        }
        prefijo = f"{prefijos.get(self.tipo, 'MAS')}-{hoy}-"

        ultimo = MovimientoMasivo.objects.filter(
            numero_boleta__startswith=prefijo
        ).order_by('-numero_boleta').first()

        if ultimo:
            try:
                ultimo_numero = int(ultimo.numero_boleta.split('-')[-1])
                nuevo_numero = ultimo_numero + 1
            except (ValueError, IndexError):
                nuevo_numero = 1
        else:
            nuevo_numero = 1

        numero_boleta = f"{prefijo}{nuevo_numero:04d}"

        while MovimientoMasivo.objects.filter(numero_boleta=numero_boleta).exists():
            nuevo_numero += 1
            numero_boleta = f"{prefijo}{nuevo_numero:04d}"

        return numero_boleta

    def __str__(self):
        return f"{self.get_tipo_display()} - {self.numero_boleta}"

    class Meta:
        verbose_name = 'Movimiento Masivo'
        verbose_name_plural = 'Movimientos Masivos'
        ordering = ['-created_at']


# ============================================================
# MOVIMIENTO (individual)
# ============================================================

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
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, related_name='movimientos')
    bodega_origen = models.ForeignKey(
        Bodega,
        on_delete=models.CASCADE,
        related_name='movimientos_origen',
        null=True,
        blank=True
    )
    bodega_destino = models.ForeignKey(
        Bodega,
        on_delete=models.CASCADE,
        related_name='movimientos_destino',
        null=True,
        blank=True
    )
    cantidad = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    descripcion = models.TextField(blank=True)

    # Relación con unidad (solo para productos con número de serie)
    unidad = models.ForeignKey(
        Unidad,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='movimientos',
        help_text='Unidad específica (solo para productos con número de serie)'
    )

    # Relación con movimiento masivo (opcional)
    movimiento_masivo = models.ForeignKey(
        MovimientoMasivo,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='movimientos_detalle'
    )

    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.numero_boleta:
            self.numero_boleta = self._generar_numero_boleta()
        super().save(*args, **kwargs)

    def _generar_numero_boleta(self):
        import datetime
        hoy = datetime.datetime.now().strftime('%Y%m%d')
        prefijo = f"BOL-{hoy}-"

        ultimo = Movimiento.objects.filter(
            numero_boleta__startswith=prefijo
        ).order_by('-numero_boleta').first()

        if ultimo:
            try:
                ultimo_numero = int(ultimo.numero_boleta.split('-')[-1])
                nuevo_numero = ultimo_numero + 1
            except (ValueError, IndexError):
                nuevo_numero = 1
        else:
            nuevo_numero = 1

        numero_boleta = f"{prefijo}{nuevo_numero:04d}"

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