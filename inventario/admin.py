from django.contrib import admin
from .models import (
    Bodega, Categoria, Producto, Unidad,
    Inventario, MovimientoMasivo, Movimiento,
    EstadoUnidad, EquipoInstalado, Cliente, Contrato , EquipoDevuelto
)


# ============================================================
# BODEGA
# ============================================================

@admin.register(Bodega)
class BodegaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'ubicacion', 'activa', 'created_at')
    list_filter = ('activa',)
    search_fields = ('nombre', 'ubicacion')
    ordering = ('nombre',)
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('nombre', 'ubicacion', 'descripcion')
        }),
        ('Estado', {
            'fields': ('activa',)
        }),
    )


# ============================================================
# CATEGORÍA
# ============================================================

@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'descripcion', 'created_at')
    search_fields = ('nombre',)
    ordering = ('nombre',)


# ============================================================
# PRODUCTO
# ============================================================

@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = (
        'codigo', 'nombre', 'categoria', 'precio',
        'maneja_serie', 'stock_total_display', 'created_at'
    )
    list_filter = ('maneja_serie', 'categoria')
    search_fields = ('nombre', 'codigo', 'descripcion')
    ordering = ('nombre',)
    list_per_page = 25
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('nombre', 'descripcion', 'categoria', 'codigo')
        }),
        ('Precios', {
            'fields': ('precio', 'precio_costo')
        }),
        ('Inventario', {
            'fields': ('maneja_serie', 'stock_minimo')
        }),
    )
    
    def stock_total_display(self, obj):
        """Muestra el stock total del producto"""
        total = obj.stock_total
        return f"{total} unidades"
    stock_total_display.short_description = 'Stock Total'


# ============================================================
# UNIDAD
# ============================================================

@admin.register(Unidad)
class UnidadAdmin(admin.ModelAdmin):
    list_display = (
        'numero_serie', 'producto', 'bodega',
        'estado', 'created_at' , 'condicion'
    )
    list_filter = ('estado', 'bodega', 'producto__categoria' , 'condicion')
    search_fields = ('numero_serie', 'producto__nombre', 'producto__codigo')
    ordering = ('producto', 'numero_serie')
    list_per_page = 25
    autocomplete_fields = ('producto',)
    list_select_related = ('producto', 'bodega', 'estado')  # ← Optimización
    list_editable = ('condicion',)  # ← Editable en línea
    
    fieldsets = (
        ('Información de la Unidad', {
            'fields': ('producto', 'numero_serie', 'bodega')
        }),
        ('Estado y Condición', {
            'fields': ('estado', 'notas' , 'condicion')
        }),
    )


# ============================================================
# INVENTARIO
# ============================================================

@admin.register(Inventario)
class InventarioAdmin(admin.ModelAdmin):
    list_display = (
        'producto', 'bodega', 'cantidad',
        'stock_minimo', 'estado_stock'
    )
    list_filter = ('bodega', 'producto__categoria')
    search_fields = ('producto__nombre', 'producto__codigo', 'bodega__nombre')
    ordering = ('bodega', 'producto__nombre')
    list_per_page = 25
    autocomplete_fields = ('producto', 'bodega')
    
    def estado_stock(self, obj):
        """Muestra si el stock está bajo"""
        if obj.cantidad <= obj.stock_minimo:
            return f"⚠️ BAJO ({obj.cantidad})"
        return f"✅ OK ({obj.cantidad})"
    estado_stock.short_description = 'Estado'


# ============================================================
# MOVIMIENTO MASIVO
# ============================================================

@admin.register(MovimientoMasivo)
class MovimientoMasivoAdmin(admin.ModelAdmin):
    list_display = (
        'numero_boleta', 'tipo', 'bodega',
        'bodega_destino', 'numero_adendum',
        'total_items', 'usuario', 'created_at'
    )
    list_filter = ('tipo', 'bodega', 'bodega_destino', 'created_at')
    search_fields = ('numero_boleta', 'numero_adendum', 'descripcion')
    ordering = ('-created_at',)
    list_per_page = 25
    readonly_fields = ('numero_boleta', 'created_at', 'updated_at')
    
    fieldsets = (
        ('Información del Movimiento', {
            'fields': ('tipo', 'numero_boleta', 'numero_adendum')
        }),
        ('Bodegas', {
            'fields': ('bodega', 'bodega_destino')
        }),
        ('Detalles', {
            'fields': ('descripcion', 'usuario')
        }),
        ('Fechas', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def total_items(self, obj):
        """Muestra el total de items del movimiento"""
        return obj.movimientos_detalle.count()
    total_items.short_description = 'Items'


# ============================================================
# MOVIMIENTO
# ============================================================

@admin.register(Movimiento)
class MovimientoAdmin(admin.ModelAdmin):
    list_display = (
        'numero_boleta', 'tipo', 'producto',
        'unidad_display', 'cantidad',
        'bodega_origen', 'bodega_destino',
        'usuario', 'created_at'
    )
    list_filter = ('tipo', 'bodega_origen', 'bodega_destino', 'created_at')
    search_fields = (
        'numero_boleta', 'numero_adendum',
        'producto__nombre', 'producto__codigo',
        'unidad__numero_serie'
    )
    ordering = ('-created_at',)
    list_per_page = 25
    readonly_fields = ('numero_boleta', 'created_at', 'updated_at')
    autocomplete_fields = ('producto', 'unidad')
    
    fieldsets = (
        ('Información del Movimiento', {
            'fields': ('tipo', 'numero_boleta', 'numero_adendum')
        }),
        ('Producto', {
            'fields': ('producto', 'unidad', 'cantidad')
        }),
        ('Bodegas', {
            'fields': ('bodega_origen', 'bodega_destino')
        }),
        ('Detalles', {
            'fields': ('descripcion', 'usuario', 'movimiento_masivo')
        }),
        ('Fechas', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def unidad_display(self, obj):
        """Muestra el número de serie si tiene unidad"""
        if obj.unidad:
            return obj.unidad.numero_serie
        return '-'
    unidad_display.short_description = 'N° Serie'


# ============================================================
# ESTADO DE UNIDAD
# ============================================================

@admin.register(EstadoUnidad)
class EstadoUnidadAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'color_badge', 'es_estado_final', 'activo', 'orden')
    list_filter = ('activo', 'es_estado_final', 'color')
    search_fields = ('nombre', 'descripcion')
    ordering = ('orden', 'nombre')
    list_editable = ('activo', 'orden')
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('nombre', 'descripcion')
        }),
        ('Configuración Visual', {
            'fields': ('color', 'orden')
        }),
        ('Configuración del Estado', {
            'fields': ('es_estado_final', 'activo'),
            'description': 'El estado "final" indica que la unidad ya no puede cambiar de estado'
        }),
    )
    
    def color_badge(self, obj):
        """Muestra el color como un badge"""
        return f'<span class="badge" style="background-color: {obj.color}; color: white; padding: 4px 8px; border-radius: 4px;">{obj.get_color_display()}</span>'
    color_badge.short_description = 'Color'
    color_badge.allow_tags = True

from .models import (
    Bodega, Categoria, Producto, Unidad,
    Inventario, MovimientoMasivo, Movimiento,
    EstadoUnidad, EquipoInstalado  # ← NUEVO
)

@admin.register(EquipoInstalado)
class EquipoInstaladoAdmin(admin.ModelAdmin):
    list_display = (
        'numero_serie', 'producto_nombre', 'cliente', 'contrato',
        'estado_final', 'numero_boleta', 'fecha_salida' 
    )
    list_filter = ('estado_final',  'cliente', 'contrato', 'bodega_origen_nombre', 'fecha_salida')
    search_fields = ('numero_serie', 'producto_nombre', 'numero_boleta', 'cliente__nombre', 'contrato__numero_contrato')
    ordering = ('-fecha_salida',)
    autocomplete_fields = ('cliente', 'contrato')
    list_per_page = 25
    readonly_fields = ('created_at',)

from .models import (
    Bodega, Categoria, Producto, Unidad,
    Inventario, MovimientoMasivo, Movimiento,
    EstadoUnidad, EquipoInstalado, Cliente  # ← Agregar Cliente
)

@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'cedula', 'contacto', 'telefono', 'email', 'activo', 'total_equipos_display' , 'total_contratos_display')
    list_filter = ('activo',)
    search_fields = ('nombre', 'cedula', 'contacto', 'telefono', 'email')
    ordering = ('nombre',)
    list_editable = ('activo',)
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('nombre', 'cedula', 'contacto')
        }),
        ('Contacto', {
            'fields': ('telefono', 'email', 'direccion')
        }),
        ('Otros', {
            'fields': ('notas', 'activo')
        }),
    )
    
    def total_equipos_display(self, obj):
        return obj.total_equipos
    total_equipos_display.short_description = 'Equipos'

    def total_contratos_display(self, obj):
        return obj.contratos.count()
    total_contratos_display.short_description = 'Contratos'



@admin.register(Contrato)
class ContratoAdmin(admin.ModelAdmin):
    list_display = ('numero_contrato', 'cliente', 'estado', 'fecha_inicio', 'fecha_fin', 'monto_mensual')
    list_filter = ('estado', 'fecha_inicio', 'cliente')
    search_fields = ('numero_contrato', 'cliente__nombre', 'descripcion')
    ordering = ('-created_at',)
    autocomplete_fields = ('cliente',)
    list_editable = ('estado',)
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('numero_contrato', 'cliente', 'estado')
        }),
        ('Vigencia', {
            'fields': ('fecha_inicio', 'fecha_fin', 'monto_mensual')
        }),
        ('Detalles', {
            'fields': ('descripcion', 'notas')
        }),
    )

@admin.register(EquipoDevuelto)
class EquipoDevueltoAdmin(admin.ModelAdmin):
    list_display = (
        'numero_boleta_devolucion', 'numero_serie', 'producto_nombre',
        'numero_contrato', 'cliente_nombre', 'estado_devolucion',
        'bodega_recepcion_nombre', 'fecha_devolucion'
    )
    list_filter = ('estado_devolucion', 'bodega_recepcion_nombre', 'fecha_devolucion')
    search_fields = (
        'numero_serie', 'producto_nombre', 'producto_codigo',
        'numero_contrato', 'cliente_nombre', 'numero_boleta_devolucion'
    )
    ordering = ('-fecha_devolucion',)
    list_per_page = 25
    list_editable = ('estado_devolucion',)
    readonly_fields = ('numero_boleta_devolucion', 'created_at', 'updated_at')

