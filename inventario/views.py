from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.contrib import messages
from django.db import models
from django.db.models import Q, Sum
from django.urls import reverse_lazy
from .models import Producto, Categoria, Movimiento, Bodega, Inventario
from .forms import ProductoForm, MovimientoForm, EntradaForm, SalidaForm, TrasladoForm, InventarioForm , TrasladoMasivoForm
import json
from django.http import JsonResponse
from django.core.serializers.json import DjangoJSONEncoder
from .forms import EntradaMasivaForm, SalidaMasivaForm
from .models import MovimientoMasivo , Unidad 
from .forms import UnidadForm, UnidadMasivaForm
import io
from django.http import FileResponse
from django.template.loader import render_to_string
from weasyprint import HTML
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from django.http import HttpResponse
from datetime import datetime


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
        return redirect('inventario:lista_productos')  # <--- CORREGIDO
    
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



# ============================================================
# MOVIMIENTOS MASIVOS
# ============================================================

@login_required
def entrada_masiva(request):
    """Vista para registrar entrada masiva de productos"""
    if request.method == 'POST':
        form = EntradaMasivaForm(request.POST)
        productos_json = request.POST.get('productos_json', '[]')
        
        if form.is_valid():
            try:
                productos = json.loads(productos_json)
            except json.JSONDecodeError:
                messages.error(request, 'Error al procesar los productos.')
                return render(request, 'inventario/movimiento_masivo_form.html', {
                    'form': form, 'titulo': 'Entrada Masiva', 'tipo': 'entrada'
                })
            
            if not productos:
                messages.error(request, 'Debes agregar al menos un producto.')
                return render(request, 'inventario/movimiento_masivo_form.html', {
                    'form': form, 'titulo': 'Entrada Masiva', 'tipo': 'entrada'
                })
            
            bodega = form.cleaned_data['bodega_destino']
            
            movimiento_masivo = MovimientoMasivo.objects.create(
                tipo=MovimientoMasivo.TIPO_ENTRADA,
                numero_adendum=form.cleaned_data.get('numero_adendum', ''),
                bodega=bodega,
                descripcion=form.cleaned_data.get('descripcion', ''),
                usuario=request.user
            )
            
            for prod_data in productos:
                try:
                    producto = Producto.objects.get(pk=prod_data['producto_id'])
                    cantidad = int(prod_data.get('cantidad', 1))
                    
                    if cantidad <= 0:
                        continue
                    
                    # ============================================================
                    # Productos CON número de serie
                    # ============================================================
                    if producto.maneja_serie:
                        series = prod_data.get('series', [])
                        for numero_serie in series:
                            # Verificar que la unidad existe
                            try:
                                unidad = Unidad.objects.get(
                                    producto=producto,
                                    numero_serie=numero_serie
                                )
                            except Unidad.DoesNotExist:
                                continue
                            
                            # Crear movimiento
                            Movimiento.objects.create(
                                tipo=Movimiento.TIPO_ENTRADA,
                                producto=producto,
                                bodega_destino=bodega,
                                cantidad=1,
                                descripcion=f"Entrada masiva - Boleta: {movimiento_masivo.numero_boleta}",
                                usuario=request.user,
                                movimiento_masivo=movimiento_masivo,
                                unidad=unidad
                            )
                            
                            # Mover unidad a la bodega
                            unidad.bodega = bodega
                            unidad.save()
                            
                            # Actualizar inventario
                            inventario, created = Inventario.objects.get_or_create(
                                producto=producto,
                                bodega=bodega,
                                defaults={'cantidad': 0, 'stock_minimo': producto.stock_minimo}
                            )
                            inventario.cantidad += 1
                            inventario.save()
                    
                    # ============================================================
                    # Productos SIN número de serie
                    # ============================================================
                    else:
                        Movimiento.objects.create(
                            tipo=Movimiento.TIPO_ENTRADA,
                            producto=producto,
                            bodega_destino=bodega,
                            cantidad=cantidad,
                            descripcion=f"Entrada masiva - Boleta: {movimiento_masivo.numero_boleta}",
                            usuario=request.user,
                            movimiento_masivo=movimiento_masivo
                        )
                        
                        inventario, created = Inventario.objects.get_or_create(
                            producto=producto,
                            bodega=bodega,
                            defaults={'cantidad': 0, 'stock_minimo': producto.stock_minimo}
                        )
                        inventario.cantidad += cantidad
                        inventario.save()
                        
                except (Producto.DoesNotExist, ValueError, KeyError) as e:
                    continue
            
            messages.success(request, f'Entrada masiva registrada. Boleta: {movimiento_masivo.numero_boleta}')
            return redirect('inventario:detalle_movimiento_masivo', pk=movimiento_masivo.pk)
    else:
        form = EntradaMasivaForm()
    
    productos_list = list(Producto.objects.all().order_by('nombre').values(
        'id', 'nombre', 'codigo', 'precio', 'maneja_serie'
    ))
    for p in productos_list:
        p['precio'] = str(p['precio'])
    
    context = {
        'form': form,
        'titulo': 'Entrada Masiva',
        'tipo': 'entrada',
        'productos_json': json.dumps(productos_list),
    }
    return render(request, 'inventario/movimiento_masivo_form.html', context)

@login_required
def salida_masiva(request):
    """Vista para registrar salida masiva de productos"""
    if request.method == 'POST':
        form = SalidaMasivaForm(request.POST)
        productos_json = request.POST.get('productos_json', '[]')
        
        if form.is_valid():
            try:
                productos = json.loads(productos_json)
            except json.JSONDecodeError:
                messages.error(request, 'Error al procesar los productos.')
                return render(request, 'inventario/movimiento_masivo_form.html', {
                    'form': form, 'titulo': 'Salida Masiva', 'tipo': 'salida'
                })
            
            if not productos:
                messages.error(request, 'Debes agregar al menos un producto.')
                return render(request, 'inventario/movimiento_masivo_form.html', {
                    'form': form, 'titulo': 'Salida Masiva', 'tipo': 'salida'
                })
            
            bodega_origen = form.cleaned_data['bodega_origen']
            
            # Validar stock antes de procesar
            errores = []
            for prod_data in productos:
                try:
                    producto = Producto.objects.get(pk=prod_data['producto_id'])
                    
                    if producto.maneja_serie:
                        # Validar que las unidades existan y estén en la bodega
                        series = prod_data.get('series', [])
                        for numero_serie in series:
                            try:
                                unidad = Unidad.objects.get(
                                    producto=producto,
                                    numero_serie=numero_serie,
                                    bodega=bodega_origen
                                )
                            except Unidad.DoesNotExist:
                                errores.append(f"{producto.nombre} - {numero_serie}: unidad no encontrada en la bodega")
                    else:
                        cantidad = int(prod_data.get('cantidad', 1))
                        inventario = Inventario.objects.filter(
                            producto=producto, bodega=bodega_origen
                        ).first()
                        if not inventario or inventario.cantidad < cantidad:
                            disponible = inventario.cantidad if inventario else 0
                            errores.append(f"{producto.nombre}: stock insuficiente (disponible: {disponible})")
                except (Producto.DoesNotExist, ValueError, KeyError):
                    continue
            
            if errores:
                for error in errores:
                    messages.error(request, error)
                return render(request, 'inventario/movimiento_masivo_form.html', {
                    'form': form, 'titulo': 'Salida Masiva', 'tipo': 'salida'
                })
            
            movimiento_masivo = MovimientoMasivo.objects.create(
                tipo=MovimientoMasivo.TIPO_SALIDA,
                numero_adendum=form.cleaned_data['numero_adendum'],
                bodega=bodega_origen,
                descripcion=form.cleaned_data.get('descripcion', ''),
                usuario=request.user
            )
            
            for prod_data in productos:
                try:
                    producto = Producto.objects.get(pk=prod_data['producto_id'])
                    
                    if producto.maneja_serie:
                        # Salida de unidades individuales
                        series = prod_data.get('series', [])
                        for numero_serie in series:
                            try:
                                unidad = Unidad.objects.get(
                                    producto=producto,
                                    numero_serie=numero_serie,
                                    bodega=bodega_origen
                                )
                            except Unidad.DoesNotExist:
                                continue
                            
                            Movimiento.objects.create(
                                tipo=Movimiento.TIPO_SALIDA,
                                producto=producto,
                                bodega_origen=bodega_origen,
                                cantidad=1,
                                descripcion=f"Salida masiva - Boleta: {movimiento_masivo.numero_boleta}",
                                usuario=request.user,
                                movimiento_masivo=movimiento_masivo,
                                unidad=unidad
                            )
                            
                            # Eliminar la unidad (salida definitiva)
                            # O cambiar su estado:
                            unidad.estado = 'vendido'
                            unidad.bodega = None
                            unidad.save()
                            
                            # Actualizar inventario
                            try:
                                inventario = Inventario.objects.get(
                                    producto=producto, bodega=bodega_origen
                                )
                                inventario.cantidad -= 1
                                inventario.save()
                            except Inventario.DoesNotExist:
                                pass
                    else:
                        cantidad = int(prod_data.get('cantidad', 1))
                        
                        Movimiento.objects.create(
                            tipo=Movimiento.TIPO_SALIDA,
                            producto=producto,
                            bodega_origen=bodega_origen,
                            cantidad=cantidad,
                            descripcion=f"Salida masiva - Boleta: {movimiento_masivo.numero_boleta}",
                            usuario=request.user,
                            movimiento_masivo=movimiento_masivo
                        )
                        
                        inventario = Inventario.objects.get(
                            producto=producto, bodega=bodega_origen
                        )
                        inventario.cantidad -= cantidad
                        inventario.save()
                        
                except (Producto.DoesNotExist, ValueError, KeyError):
                    continue
            
            messages.success(request, f'Salida masiva registrada. Boleta: {movimiento_masivo.numero_boleta}')
            return redirect('inventario:detalle_movimiento_masivo', pk=movimiento_masivo.pk)
    else:
        form = SalidaMasivaForm()
    
    productos_list = list(Producto.objects.all().order_by('nombre').values(
        'id', 'nombre', 'codigo', 'precio', 'maneja_serie'
    ))
    for p in productos_list:
        p['precio'] = str(p['precio'])
    
    context = {
        'form': form,
        'titulo': 'Salida Masiva',
        'tipo': 'salida',
        'productos_json': json.dumps(productos_list),
    }
    return render(request, 'inventario/movimiento_masivo_form.html', context)


@login_required
def detalle_movimiento_masivo(request, pk):
    """Muestra el detalle de un movimiento masivo"""
    movimiento_masivo = get_object_or_404(MovimientoMasivo, pk=pk)
    movimientos_detalle = movimiento_masivo.movimientos_detalle.select_related(
        'producto', 'unidad'
    ).all()
    
    context = {
        'movimiento_masivo': movimiento_masivo,
        'movimientos_detalle': movimientos_detalle,
    }
    return render(request, 'inventario/movimiento_masivo_detail.html', context)


@login_required
def lista_movimientos_masivos(request):
    """Lista todos los movimientos masivos"""
    movimientos_masivos = MovimientoMasivo.objects.all()
    
    context = {
        'movimientos_masivos': movimientos_masivos,
    }
    return render(request, 'inventario/movimiento_masivo_list.html', context)

@login_required
def traslado_masivo(request):
    """Vista para registrar traslado masivo de productos entre bodegas"""
    if request.method == 'POST':
        form = TrasladoMasivoForm(request.POST)
        productos_json = request.POST.get('productos_json', '[]')
        
        if form.is_valid():
            try:
                productos = json.loads(productos_json)
            except json.JSONDecodeError:
                messages.error(request, 'Error al procesar los productos.')
                return render(request, 'inventario/movimiento_masivo_form.html', {
                    'form': form, 'titulo': 'Traslado Masivo', 'tipo': 'traslado'
                })
            
            if not productos:
                messages.error(request, 'Debes agregar al menos un producto.')
                return render(request, 'inventario/movimiento_masivo_form.html', {
                    'form': form, 'titulo': 'Traslado Masivo', 'tipo': 'traslado'
                })
            
            bodega_origen = form.cleaned_data['bodega_origen']
            bodega_destino = form.cleaned_data['bodega_destino']
            
            # ============================================================
            # VALIDAR PRODUCTOS
            # ============================================================
            errores = []
            productos_validos = []
            
            for prod_data in productos:
                try:
                    producto = Producto.objects.get(pk=prod_data['producto_id'])
                    
                    if producto.maneja_serie:
                        series = prod_data.get('series', [])
                        if not series:
                            errores.append(f"{producto.nombre}: no hay series seleccionadas")
                            continue
                        
                        series_validas = []
                        for numero_serie in series:
                            try:
                                Unidad.objects.get(
                                    producto=producto,
                                    numero_serie=numero_serie,
                                    bodega=bodega_origen
                                )
                                series_validas.append(numero_serie)
                            except Unidad.DoesNotExist:
                                errores.append(f"{producto.nombre} - {numero_serie}: unidad no encontrada en origen")
                        
                        if series_validas:
                            prod_data['series'] = series_validas
                            productos_validos.append(prod_data)
                    else:
                        cantidad = int(prod_data.get('cantidad', 0))
                        if cantidad <= 0:
                            errores.append(f"{producto.nombre}: cantidad inválida")
                            continue
                        
                        inventario = Inventario.objects.filter(
                            producto=producto, bodega=bodega_origen
                        ).first()
                        
                        if not inventario or inventario.cantidad < cantidad:
                            disponible = inventario.cantidad if inventario else 0
                            errores.append(f"{producto.nombre}: stock insuficiente (disponible: {disponible})")
                            continue
                        
                        productos_validos.append(prod_data)
                except (Producto.DoesNotExist, ValueError, KeyError) as e:
                    errores.append(f"Error con producto: {str(e)}")
                    continue
            
            if errores:
                for error in errores:
                    messages.error(request, error)
                return render(request, 'inventario/movimiento_masivo_form.html', {
                    'form': form, 'titulo': 'Traslado Masivo', 'tipo': 'traslado'
                })
            
            if not productos_validos:
                messages.error(request, 'No hay productos válidos para procesar.')
                return render(request, 'inventario/movimiento_masivo_form.html', {
                    'form': form, 'titulo': 'Traslado Masivo', 'tipo': 'traslado'
                })
            
            # ============================================================
            # CREAR MOVIMIENTO MASIVO
            # ============================================================
            movimiento_masivo = MovimientoMasivo.objects.create(
                tipo=MovimientoMasivo.TIPO_TRASLADO,
                numero_adendum=form.cleaned_data.get('numero_adendum', ''),
                bodega=bodega_origen,
                bodega_destino=bodega_destino,
                descripcion=form.cleaned_data.get('descripcion', ''),
                usuario=request.user
            )
            
            # ============================================================
            # PROCESAR PRODUCTOS
            # ============================================================
            for prod_data in productos_validos:
                try:
                    producto = Producto.objects.get(pk=prod_data['producto_id'])
                    
                    if producto.maneja_serie:
                        series = prod_data.get('series', [])
                        for numero_serie in series:
                            try:
                                unidad = Unidad.objects.get(
                                    producto=producto,
                                    numero_serie=numero_serie,
                                    bodega=bodega_origen
                                )
                            except Unidad.DoesNotExist:
                                continue
                            
                            Movimiento.objects.create(
                                tipo=Movimiento.TIPO_TRASLADO,
                                producto=producto,
                                bodega_origen=bodega_origen,
                                bodega_destino=bodega_destino,
                                cantidad=1,  # ← Siempre 1 para productos con serie
                                descripcion=f"Traslado masivo - Boleta: {movimiento_masivo.numero_boleta}",
                                usuario=request.user,
                                movimiento_masivo=movimiento_masivo,
                                unidad=unidad
                            )
                            
                            unidad.bodega = bodega_destino
                            unidad.save()
                            
                            try:
                                inv_origen = Inventario.objects.get(
                                    producto=producto, bodega=bodega_origen
                                )
                                inv_origen.cantidad -= 1
                                inv_origen.save()
                            except Inventario.DoesNotExist:
                                pass
                            
                            inv_destino, created = Inventario.objects.get_or_create(
                                producto=producto,
                                bodega=bodega_destino,
                                defaults={'cantidad': 0, 'stock_minimo': producto.stock_minimo}
                            )
                            inv_destino.cantidad += 1
                            inv_destino.save()
                    else:
                        cantidad = int(prod_data.get('cantidad', 0))
                        
                        Movimiento.objects.create(
                            tipo=Movimiento.TIPO_TRASLADO,
                            producto=producto,
                            bodega_origen=bodega_origen,
                            bodega_destino=bodega_destino,
                            cantidad=cantidad,
                            descripcion=f"Traslado masivo - Boleta: {movimiento_masivo.numero_boleta}",
                            usuario=request.user,
                            movimiento_masivo=movimiento_masivo
                        )
                        
                        try:
                            inv_origen = Inventario.objects.get(
                                producto=producto, bodega=bodega_origen
                            )
                            inv_origen.cantidad -= cantidad
                            inv_origen.save()
                        except Inventario.DoesNotExist:
                            pass
                        
                        inv_destino, created = Inventario.objects.get_or_create(
                            producto=producto,
                            bodega=bodega_destino,
                            defaults={'cantidad': 0, 'stock_minimo': producto.stock_minimo}
                        )
                        inv_destino.cantidad += cantidad
                        inv_destino.save()
                        
                except (Producto.DoesNotExist, ValueError, KeyError):
                    continue
            
            messages.success(request, f'Traslado masivo registrado. Boleta: {movimiento_masivo.numero_boleta}')
            return redirect('inventario:detalle_movimiento_masivo', pk=movimiento_masivo.pk)
    else:
        form = TrasladoMasivoForm()
    
    productos_list = list(Producto.objects.all().order_by('nombre').values(
        'id', 'nombre', 'codigo', 'precio', 'maneja_serie'
    ))
    for p in productos_list:
        p['precio'] = str(p['precio'])
    
    context = {
        'form': form,
        'titulo': 'Traslado Masivo',
        'tipo': 'traslado',
        'productos_json': json.dumps(productos_list),
    }
    return render(request, 'inventario/movimiento_masivo_form.html', context)

@login_required
def generar_pdf_transferencia(request, pk):
    """Genera un PDF de la transferencia con 15 items por página"""
    movimiento_masivo = get_object_or_404(MovimientoMasivo, pk=pk)
    movimientos_detalle = list(movimiento_masivo.movimientos_detalle.select_related(
        'producto', 'unidad'
    ).all())
    
    # ============================================================
    # DIVIDIR EN BLOQUES DE 25 ITEMS
    # ============================================================
    ITEMS_POR_PAGINA = 25
    bloques = []
    
    for i in range(0, len(movimientos_detalle), ITEMS_POR_PAGINA):
        bloque = movimientos_detalle[i:i + ITEMS_POR_PAGINA]
        bloques.append(bloque)
    
    # Si no hay movimientos, crear un bloque vacío
    if not bloques:
        bloques = [[]]
    
    # ============================================================
    # AGREGAR CONTADOR GLOBAL A CADA MOVIMIENTO
    # ============================================================
    contador_global = 1
    for bloque in bloques:
        for mov in bloque:
            mov.contador = contador_global
            contador_global += 1
    
    # ============================================================
    # CONTEXTO
    # ============================================================
    context = {
        'movimiento': movimiento_masivo,
        'bloques': bloques,
        'total_items': len(movimientos_detalle),
        'total_paginas': len(bloques),
    }
    
    # ============================================================
    # GENERAR PDF
    # ============================================================
    html_string = render_to_string('inventario/transferencia_pdf.html', context)
    
    buffer = io.BytesIO()
    HTML(string=html_string, base_url=request.build_absolute_uri()).write_pdf(buffer)
    buffer.seek(0)
    
    return FileResponse(
        buffer,
        as_attachment=True,
        filename=f'transferencia_{movimiento_masivo.numero_boleta}.pdf'
    )


@login_required
def exportar_bodega_excel(request, bodega_id):
    """Exporta el inventario de una bodega a un archivo Excel"""
    bodega = get_object_or_404(Bodega, pk=bodega_id)
    inventarios = Inventario.objects.filter(bodega=bodega).select_related(
        'producto', 'producto__categoria'
    ).order_by('producto__nombre')
    
    # Crear el libro de Excel
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = f"Bodega {bodega.nombre[:20]}"  # Excel limita a 31 caracteres
    
    # ============================================================
    # ESTILOS
    # ============================================================
    
    # Colores
    color_encabezado = "2C3E50"
    color_subtitulo = "3498DB"
    color_alerta = "E74C3C"
    color_normal = "F8F9FA"
    
    # Fuentes
    fuente_titulo = Font(name='Calibri', size=16, bold=True, color="2C3E50")
    fuente_subtitulo = Font(name='Calibri', size=11, bold=True, color="FFFFFF")
    fuente_encabezado = Font(name='Calibri', size=11, bold=True, color="FFFFFF")
    fuente_normal = Font(name='Calibri', size=10)
    fuente_alerta = Font(name='Calibri', size=10, bold=True, color="E74C3C")
    
    # Rellenos
    relleno_encabezado = PatternFill(start_color=color_encabezado, end_color=color_encabezado, fill_type="solid")
    relleno_subtitulo = PatternFill(start_color=color_subtitulo, end_color=color_subtitulo, fill_type="solid")
    relleno_alerta = PatternFill(start_color="FADBD8", end_color="FADBD8", fill_type="solid")
    relleno_alterno = PatternFill(start_color=color_normal, end_color=color_normal, fill_type="solid")
    
    # Alineaciones
    alineacion_centro = Alignment(horizontal="center", vertical="center")
    alineacion_izquierda = Alignment(horizontal="left", vertical="center")
    alineacion_derecha = Alignment(horizontal="right", vertical="center")
    
    # Bordes
    borde_fino = Border(
        left=Side(style='thin', color='CCCCCC'),
        right=Side(style='thin', color='CCCCCC'),
        top=Side(style='thin', color='CCCCCC'),
        bottom=Side(style='thin', color='CCCCCC')
    )
    
    # ============================================================
    # ENCABEZADO DEL REPORTE
    # ============================================================
    
    # Título principal
    ws.merge_cells('A1:G1')
    celda_titulo = ws['A1']
    celda_titulo.value = f"📦 INVENTARIO DE BODEGA: {bodega.nombre.upper()}"
    celda_titulo.font = fuente_titulo
    celda_titulo.alignment = alineacion_centro
    ws.row_dimensions[1].height = 30
    
    # Información de la bodega
    ws.merge_cells('A2:G2')
    celda_info = ws['A2']
    celda_info.value = f"Ubicación: {bodega.ubicacion or 'No especificada'}"
    celda_info.font = Font(name='Calibri', size=10, italic=True, color="7F8C8D")
    celda_info.alignment = alineacion_centro
    ws.row_dimensions[2].height = 20
    
    # Fecha de generación
    ws.merge_cells('A3:G3')
    celda_fecha = ws['A3']
    celda_fecha.value = f"Fecha de generación: {datetime.now().strftime('%d/%m/%Y %H:%M')}"
    celda_fecha.font = Font(name='Calibri', size=9, color="7F8C8D")
    celda_fecha.alignment = alineacion_centro
    ws.row_dimensions[3].height = 18
    
    # Fila vacía
    ws.row_dimensions[4].height = 10
    
    # ============================================================
    # ENCABEZADOS DE LA TABLA (Fila 5)
    # ============================================================
    
    encabezados = [
        'N°', 'Código', 'Producto', 'Categoría', 'N° Serie', 
        'Cantidad', 'Stock Mínimo', 'Estado'
    ]
    
    # Ajustar a 8 columnas (A-H)
    for col_num, encabezado in enumerate(encabezados, 1):
        celda = ws.cell(row=5, column=col_num, value=encabezado)
        celda.font = fuente_encabezado
        celda.fill = relleno_encabezado
        celda.alignment = alineacion_centro
        celda.border = borde_fino
    
    ws.row_dimensions[5].height = 25
    
    # ============================================================
    # DATOS (Desde la fila 6)
    # ============================================================
    
    fila_actual = 6
    total_items = 0
    productos_bajo_stock = 0
    
    for index, inv in enumerate(inventarios, 1):
        producto = inv.producto
        
        # Verificar si está bajo stock
        es_bajo_stock = inv.cantidad <= inv.stock_minimo
        if es_bajo_stock:
            productos_bajo_stock += 1
        
        total_items += inv.cantidad
        
        # Datos
        datos = [
            index,
            producto.codigo,
            producto.nombre,
            producto.categoria.nombre if producto.categoria else '-',
            producto.numero_serie or '-',
            inv.cantidad,
            inv.stock_minimo,
            '⚠️ BAJO' if es_bajo_stock else '✅ OK'
        ]
        
        for col_num, valor in enumerate(datos, 1):
            celda = ws.cell(row=fila_actual, column=col_num, value=valor)
            celda.font = fuente_alerta if es_bajo_stock else fuente_normal
            celda.border = borde_fino
            
            # Alineación según el tipo
            if col_num in [1, 6, 7, 8]:
                celda.alignment = alineacion_centro
            elif col_num == 4:
                celda.alignment = alineacion_izquierda
            else:
                celda.alignment = alineacion_izquierda
            
            # Fondo alternado o de alerta
            if es_bajo_stock:
                celda.fill = relleno_alerta
            elif index % 2 == 0:
                celda.fill = relleno_alterno
        
        fila_actual += 1
    
    # ============================================================
    # FILA DE TOTALES
    # ============================================================
    
    fila_actual += 1
    
    # Total de productos
    ws.merge_cells(f'A{fila_actual}:D{fila_actual}')
    celda_total_label = ws[f'A{fila_actual}']
    celda_total_label.value = "TOTAL DE PRODUCTOS:"
    celda_total_label.font = Font(name='Calibri', size=11, bold=True, color="FFFFFF")
    celda_total_label.fill = relleno_subtitulo
    celda_total_label.alignment = alineacion_derecha
    celda_total_label.border = borde_fino
    
    celda_total = ws[f'E{fila_actual}']
    celda_total.value = len(inventarios)
    celda_total.font = Font(name='Calibri', size=11, bold=True, color="FFFFFF")
    celda_total.fill = relleno_subtitulo
    celda_total.alignment = alineacion_centro
    celda_total.border = borde_fino
    
    celda_items_label = ws[f'F{fila_actual}']
    celda_items_label.value = "TOTAL ITEMS:"
    celda_items_label.font = Font(name='Calibri', size=11, bold=True, color="FFFFFF")
    celda_items_label.fill = relleno_subtitulo
    celda_items_label.alignment = alineacion_derecha
    celda_items_label.border = borde_fino
    
    celda_items = ws[f'G{fila_actual}']
    celda_items.value = total_items
    celda_items.font = Font(name='Calibri', size=11, bold=True, color="FFFFFF")
    celda_items.fill = relleno_subtitulo
    celda_items.alignment = alineacion_centro
    celda_items.border = borde_fino
    
    celda_estado = ws[f'H{fila_actual}']
    celda_estado.value = f"⚠️ {productos_bajo_stock} bajo stock" if productos_bajo_stock > 0 else "✅ Todo OK"
    celda_estado.font = Font(name='Calibri', size=10, bold=True, color="FFFFFF")
    celda_estado.fill = relleno_alerta if productos_bajo_stock > 0 else relleno_subtitulo
    celda_estado.alignment = alineacion_centro
    celda_estado.border = borde_fino
    
    ws.row_dimensions[fila_actual].height = 25
    
    # ============================================================
    # AJUSTAR ANCHO DE COLUMNAS
    # ============================================================
    
    anchos = {
        'A': 6,   # N°
        'B': 15,  # Código
        'C': 35,  # Producto
        'D': 20,  # Categoría
        'E': 20,  # N° Serie
        'F': 12,  # Cantidad
        'G': 12,  # Stock Mínimo
        'H': 15,  # Estado
    }
    
    for col, ancho in anchos.items():
        ws.column_dimensions[col].width = ancho
    
    # Congelar la fila de encabezados
    ws.freeze_panes = 'A6'
    
    # ============================================================
    # CREAR LA RESPUESTA HTTP
    # ============================================================
    
    # Nombre del archivo
    nombre_archivo = f"inventario_{bodega.nombre.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
    
    # Configurar respuesta
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="{nombre_archivo}"'
    
    # Guardar el libro en la respuesta
    wb.save(response)
    
    return response

# ============================================================
# GESTIÓN DE UNIDADES (productos con número de serie)
# ============================================================

@login_required
def lista_unidades(request, producto_id):
    """Lista todas las unidades de un producto"""
    producto = get_object_or_404(Producto, pk=producto_id)
    unidades = Unidad.objects.filter(producto=producto).select_related('bodega')
    
    # Estadísticas
    total = unidades.count()
    disponibles = unidades.filter(estado='disponible').count()
    vendidos = unidades.filter(estado='vendido').count()
    dañados = unidades.filter(estado='dañado').count()
    reservados = unidades.filter(estado='reservado').count()
    
    context = {
        'producto': producto,
        'unidades': unidades,
        'total': total,
        'disponibles': disponibles,
        'vendidos': vendidos,
        'dañados': dañados,
        'reservados': reservados,
    }
    return render(request, 'inventario/unidad_list.html', context)


@login_required
def crear_unidad(request, producto_id):
    """Crea una unidad individual para un producto"""
    producto = get_object_or_404(Producto, pk=producto_id)
    
    if not producto.maneja_serie:
        messages.error(request, 'Este producto no maneja número de serie.')
        return redirect('inventario:detalle_producto', pk=producto.pk)
    
    if request.method == 'POST':
        form = UnidadForm(request.POST)
        if form.is_valid():
            unidad = form.save(commit=False)
            unidad.producto = producto
            unidad.save()
            
            # Actualizar inventario
            if unidad.bodega:
                inventario, created = Inventario.objects.get_or_create(
                    producto=producto,
                    bodega=unidad.bodega,
                    defaults={'cantidad': 0, 'stock_minimo': producto.stock_minimo}
                )
                inventario.cantidad += 1
                inventario.save()
            
            messages.success(request, f'Unidad "{unidad.numero_serie}" creada correctamente.')
            return redirect('inventario:lista_unidades', producto_id=producto.pk)
    else:
        form = UnidadForm()
    
    context = {
        'form': form,
        'producto': producto,
        'titulo': f'Nueva Unidad - {producto.nombre}',
    }
    return render(request, 'inventario/unidad_form.html', context)


@login_required
def crear_unidades_masivas(request, producto_id):
    """Crea varias unidades a la vez"""
    producto = get_object_or_404(Producto, pk=producto_id)
    
    if not producto.maneja_serie:
        messages.error(request, 'Este producto no maneja número de serie.')
        return redirect('inventario:detalle_producto', pk=producto.pk)
    
    if request.method == 'POST':
        form = UnidadMasivaForm(request.POST)
        if form.is_valid():
            cantidad = form.cleaned_data['cantidad']
            prefijo = form.cleaned_data.get('prefijo', '')
            numero_inicial = form.cleaned_data['numero_inicial']
            bodega = form.cleaned_data['bodega']
            estado = form.cleaned_data['estado']
            
            creadas = 0
            errores = []
            
            for i in range(cantidad):
                numero = numero_inicial + i
                numero_serie = f"{prefijo}{numero:04d}"
                
                # Verificar que no exista
                if Unidad.objects.filter(numero_serie=numero_serie).exists():
                    errores.append(f"'{numero_serie}' ya existe")
                    continue
                
                try:
                    Unidad.objects.create(
                        producto=producto,
                        numero_serie=numero_serie,
                        bodega=bodega,
                        estado=estado
                    )
                    creadas += 1
                except Exception as e:
                    errores.append(f"Error con '{numero_serie}': {str(e)}")
            
            # Actualizar inventario
            if creadas > 0 and bodega:
                inventario, created = Inventario.objects.get_or_create(
                    producto=producto,
                    bodega=bodega,
                    defaults={'cantidad': 0, 'stock_minimo': producto.stock_minimo}
                )
                inventario.cantidad += creadas
                inventario.save()
            
            if errores:
                for error in errores:
                    messages.warning(request, error)
            
            if creadas > 0:
                messages.success(request, f'✅ {creadas} unidades creadas correctamente.')
            
            return redirect('inventario:lista_unidades', producto_id=producto.pk)
    else:
        form = UnidadMasivaForm()
    
    context = {
        'form': form,
        'producto': producto,
        'titulo': f'Crear Unidades Masivas - {producto.nombre}',
    }
    return render(request, 'inventario/unidad_masiva_form.html', context)


@login_required
def editar_unidad(request, pk):
    """Edita una unidad existente"""
    unidad = get_object_or_404(Unidad, pk=pk)
    producto = unidad.producto
    bodega_anterior = unidad.bodega
    
    if request.method == 'POST':
        form = UnidadForm(request.POST, instance=unidad)
        if form.is_valid():
            unidad = form.save()
            
            # Actualizar inventario si cambió de bodega
            if bodega_anterior != unidad.bodega:
                # Restar de la bodega anterior
                if bodega_anterior:
                    try:
                        inv_anterior = Inventario.objects.get(
                            producto=producto,
                            bodega=bodega_anterior
                        )
                        inv_anterior.cantidad -= 1
                        inv_anterior.save()
                    except Inventario.DoesNotExist:
                        pass
                
                # Sumar a la nueva bodega
                if unidad.bodega:
                    inv_nueva, created = Inventario.objects.get_or_create(
                        producto=producto,
                        bodega=unidad.bodega,
                        defaults={'cantidad': 0, 'stock_minimo': producto.stock_minimo}
                    )
                    inv_nueva.cantidad += 1
                    inv_nueva.save()
            
            messages.success(request, f'Unidad "{unidad.numero_serie}" actualizada.')
            return redirect('inventario:lista_unidades', producto_id=producto.pk)
    else:
        form = UnidadForm(instance=unidad)
    
    context = {
        'form': form,
        'unidad': unidad,
        'producto': producto,
        'titulo': f'Editar Unidad - {unidad.numero_serie}',
    }
    return render(request, 'inventario/unidad_form.html', context)


@login_required
def eliminar_unidad(request, pk):
    """Elimina una unidad"""
    unidad = get_object_or_404(Unidad, pk=pk)
    producto = unidad.producto
    bodega = unidad.bodega
    
    if request.method == 'POST':
        numero_serie = unidad.numero_serie
        unidad.delete()
        
        # Actualizar inventario
        if bodega:
            try:
                inventario = Inventario.objects.get(
                    producto=producto,
                    bodega=bodega
                )
                inventario.cantidad -= 1
                inventario.save()
            except Inventario.DoesNotExist:
                pass
        
        messages.success(request, f'Unidad "{numero_serie}" eliminada.')
        return redirect('inventario:lista_unidades', producto_id=producto.pk)
    
    context = {
        'unidad': unidad,
        'producto': producto,
    }
    return render(request, 'inventario/unidad_confirm_delete.html', context)

@login_required
def obtener_unidades_producto(request, producto_id):
    """API para obtener las unidades disponibles de un producto en una bodega"""
    producto = get_object_or_404(Producto, pk=producto_id)
    bodega_id = request.GET.get('bodega_id')
    
    unidades = Unidad.objects.filter(producto=producto, estado='disponible')
    
    if bodega_id:
        unidades = unidades.filter(bodega_id=bodega_id)
    
    data = [{
        'id': u.id,
        'numero_serie': u.numero_serie,
        'bodega': u.bodega.nombre if u.bodega else 'Sin asignar',
        'estado': u.get_estado_display(),
    } for u in unidades]
    
    return JsonResponse({'unidades': data})