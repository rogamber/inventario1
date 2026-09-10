from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.contrib import messages
from django.db import models
from django.db.models import Q, Sum
from django.urls import reverse_lazy
from .models import Producto, Categoria, Movimiento, Bodega, Inventario
from .forms import ProductoForm, MovimientoForm, EntradaForm, SalidaForm, TrasladoForm, InventarioForm

# Vista de inicio de sesión personalizada
class CustomLoginView(LoginView):
    template_name = 'inventario/login.html'
    redirect_authenticated_user = True
    
    def get_success_url(self):
        return reverse_lazy('inventario:lista_productos')

# ============================================================
# PÁGINA DE INICIO (INDEX)
# ============================================================

def index(request):
    """Página de inicio del sistema"""
    # Estadísticas
    total_productos = Producto.objects.count()
    total_bodegas = Bodega.objects.filter(activa=True).count()
    total_movimientos = Movimiento.objects.count()
    
    # Productos con stock bajo (si existe el modelo Inventario)
    try:
        productos_bajo_stock = Inventario.objects.filter(
            cantidad__lte=models.F('stock_minimo')
        ).count()
    except:
        productos_bajo_stock = 0
    
    # Últimos movimientos
    ultimos_movimientos = Movimiento.objects.all().order_by('-created_at')[:5]
    
    context = {
        'total_productos': total_productos,
        'total_bodegas': total_bodegas,
        'total_movimientos': total_movimientos,
        'productos_bajo_stock': productos_bajo_stock,
        'ultimos_movimientos': ultimos_movimientos,
    }
    return render(request, 'inventario/index.html', context)

# ============================================================
# PRODUCTOS
# ============================================================

@login_required
def lista_productos(request):
    query = request.GET.get('q', '')
    productos = Producto.objects.all()
    
    if query:
        productos = productos.filter(
            Q(nombre__icontains=query) |
            Q(codigo__icontains=query) |
            Q(categoria__nombre__icontains=query)
        )
    
    context = {
        'productos': productos,
        'query': query,
    }
    return render(request, 'inventario/producto_list.html', context)

@login_required
def detalle_producto(request, pk):
    producto = get_object_or_404(Producto, pk=pk)
    movimientos = Movimiento.objects.filter(producto=producto)[:10]
    
    # Obtener stock por bodega
    inventarios = Inventario.objects.filter(producto=producto).select_related('bodega')
    stock_total = sum(inv.cantidad for inv in inventarios)
    
    context = {
        'producto': producto,
        'movimientos': movimientos,
        'inventarios': inventarios,
        'stock_total': stock_total,
    }
    return render(request, 'inventario/producto_detail.html', context)

@login_required
def crear_producto(request):
    if request.method == 'POST':
        form = ProductoForm(request.POST)
        if form.is_valid():
            producto = form.save()
            
            # Registrar cantidad inicial si se especificó
            cantidad = form.cleaned_data.get('cantidad_inicial')
            bodega = form.cleaned_data.get('bodega_inicial')
            
            if cantidad and cantidad > 0 and bodega:
                # Crear registro de inventario
                inventario, created = Inventario.objects.get_or_create(
                    producto=producto,
                    bodega=bodega,
                    defaults={'cantidad': 0, 'stock_minimo': producto.stock_minimo}
                )
                inventario.cantidad += cantidad
                inventario.save()
                
                # Registrar movimiento con boleta automática
                Movimiento.objects.create(
                    tipo=Movimiento.TIPO_ENTRADA,
                    producto=producto,
                    bodega_destino=bodega,
                    cantidad=cantidad,
                    descripcion=f'Stock inicial al crear el producto',
                    usuario=request.user
                )
            
            messages.success(request, f'Producto "{producto.nombre}" creado correctamente.')
            return redirect('inventario:detalle_producto', pk=producto.pk)
    else:
        form = ProductoForm()
    
    context = {'form': form, 'titulo': 'Crear Producto'}
    return render(request, 'inventario/producto_form.html', context)

@login_required
def editar_producto(request, pk):
    producto = get_object_or_404(Producto, pk=pk)
    
    if request.method == 'POST':
        form = ProductoForm(request.POST, instance=producto)
        if form.is_valid():
            producto = form.save()
            messages.success(request, f'Producto "{producto.nombre}" actualizado correctamente.')
            return redirect('inventario:detalle_producto', pk=producto.pk)
    else:
        form = ProductoForm(instance=producto)
    
    context = {
        'form': form,
        'titulo': 'Editar Producto',
        'producto': producto,
    }
    return render(request, 'inventario/producto_form.html', context)

@login_required
def eliminar_producto(request, pk):
    producto = get_object_or_404(Producto, pk=pk)
    
    if request.method == 'POST':
        nombre = producto.nombre
        producto.delete()
        messages.success(request, f'Producto "{nombre}" eliminado correctamente.')
        return redirect('inventario:lista_productos')
    
    context = {'producto': producto}
    return render(request, 'inventario/producto_confirm_delete.html', context)

# ============================================================
# BODEGAS
# ============================================================

@login_required
def lista_bodegas(request):
    bodegas = Bodega.objects.all()
    context = {'bodegas': bodegas}
    return render(request, 'inventario/bodega_list.html', context)

@login_required
def crear_bodega(request):
    if request.method == 'POST':
        nombre = request.POST.get('nombre')
        ubicacion = request.POST.get('ubicacion')
        descripcion = request.POST.get('descripcion')
        
        if nombre:
            Bodega.objects.create(
                nombre=nombre,
                ubicacion=ubicacion,
                descripcion=descripcion
            )
            messages.success(request, f'Bodega "{nombre}" creada correctamente.')
            return redirect('inventario:lista_bodegas')
    
    return render(request, 'inventario/bodega_form.html')

@login_required
def editar_bodega(request, pk):
    bodega = get_object_or_404(Bodega, pk=pk)
    
    if request.method == 'POST':
        bodega.nombre = request.POST.get('nombre')
        bodega.ubicacion = request.POST.get('ubicacion')
        bodega.descripcion = request.POST.get('descripcion')
        bodega.activa = request.POST.get('activa') == 'on'
        bodega.save()
        messages.success(request, f'Bodega "{bodega.nombre}" actualizada correctamente.')
        return redirect('inventario:lista_bodegas')
    
    context = {'bodega': bodega}
    return render(request, 'inventario/bodega_form.html', context)

# ============================================================
# MOVIMIENTOS
# ============================================================

@login_required
def lista_movimientos(request):
    movimientos = Movimiento.objects.all()
    context = {'movimientos': movimientos}
    return render(request, 'inventario/movimiento_list.html', context)

@login_required
def detalle_movimiento(request, pk):
    movimiento = get_object_or_404(Movimiento, pk=pk)
    context = {'movimiento': movimiento}
    return render(request, 'inventario/movimiento_detail.html', context)

@login_required
def entrada_producto(request):
    if request.method == 'POST':
        form = EntradaForm(request.POST)
        if form.is_valid():
            movimiento = form.save(commit=False)
            movimiento.tipo = Movimiento.TIPO_ENTRADA
            movimiento.usuario = request.user
            movimiento.save()
            
            # Actualizar inventario
            inventario, created = Inventario.objects.get_or_create(
                producto=movimiento.producto,
                bodega=movimiento.bodega_destino
            )
            inventario.cantidad += movimiento.cantidad
            inventario.save()
            
            messages.success(request, f'Entrada registrada. Boleta: {movimiento.numero_boleta}')
            return redirect('inventario:lista_movimientos')
    else:
        form = EntradaForm()
    
    context = {'form': form, 'titulo': 'Registrar Entrada', 'tipo': 'entrada'}
    return render(request, 'inventario/movimiento_form.html', context)

# inventario/views.py

@login_required
def salida_producto(request):
    if request.method == 'POST':
        form = SalidaForm(request.POST)
        if form.is_valid():
            movimiento = form.save(commit=False)
            movimiento.tipo = Movimiento.TIPO_SALIDA
            movimiento.usuario = request.user
            movimiento.save()
            
            # Actualizar inventario
            inventario = Inventario.objects.get(
                producto=movimiento.producto,
                bodega=movimiento.bodega_origen
            )
            inventario.cantidad -= movimiento.cantidad
            inventario.save()
            
            messages.success(
                request, 
                f'Salida registrada. Boleta: {movimiento.numero_boleta} | Adendum: {movimiento.numero_adendum}'
            )
            return redirect('inventario:lista_movimientos')
    else:
        form = SalidaForm()
    
    context = {'form': form, 'titulo': 'Registrar Salida', 'tipo': 'salida'}
    return render(request, 'inventario/movimiento_form.html', context)

@login_required
def traslado_producto(request):
    if request.method == 'POST':
        form = TrasladoForm(request.POST)
        if form.is_valid():
            movimiento = form.save(commit=False)
            movimiento.tipo = Movimiento.TIPO_TRASLADO
            movimiento.usuario = request.user
            movimiento.save()
            
            # Restar de origen
            inventario_origen = Inventario.objects.get(
                producto=movimiento.producto,
                bodega=movimiento.bodega_origen
            )
            inventario_origen.cantidad -= movimiento.cantidad
            inventario_origen.save()
            
            # Sumar a destino
            inventario_destino, created = Inventario.objects.get_or_create(
                producto=movimiento.producto,
                bodega=movimiento.bodega_destino
            )
            inventario_destino.cantidad += movimiento.cantidad
            inventario_destino.save()
            
            messages.success(request, f'Traslado registrado. Boleta: {movimiento.numero_boleta}')
            return redirect('inventario:lista_movimientos')
    else:
        form = TrasladoForm()
    
    context = {'form': form, 'titulo': 'Registrar Traslado', 'tipo': 'traslado'}
    return render(request, 'inventario/movimiento_form.html', context)

# ============================================================
# INVENTARIO POR BODEGA
# ============================================================

@login_required
def inventario_por_bodega(request, bodega_id):
    bodega = get_object_or_404(Bodega, pk=bodega_id)
    inventarios = Inventario.objects.filter(bodega=bodega).select_related('producto')
    context = {'bodega': bodega, 'inventarios': inventarios}
    return render(request, 'inventario/inventario_bodega.html', context)

# ============================================================
# RESUMEN DE INVENTARIO
# ============================================================

@login_required
def resumen_inventario(request):
    bodegas = Bodega.objects.filter(activa=True)
    productos = Producto.objects.all()
    
    # Resumen por bodega
    resumen = []
    for bodega in bodegas:
        total_productos = Inventario.objects.filter(bodega=bodega).count()
        total_items = Inventario.objects.filter(bodega=bodega).aggregate(Sum('cantidad'))['cantidad__sum'] or 0
        resumen.append({
            'bodega': bodega,
            'total_productos': total_productos,
            'total_items': total_items
        })
    
    context = {
        'resumen': resumen,
        'total_bodegas': bodegas.count(),
        'total_productos': productos.count(),
    }
    return render(request, 'inventario/resumen_inventario.html', context)