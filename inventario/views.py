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
from .models import MovimientoMasivo
import io
from django.http import FileResponse
from django.template.loader import render_to_string
from weasyprint import HTML

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
            
            movimiento_masivo = MovimientoMasivo.objects.create(
                tipo=MovimientoMasivo.TIPO_ENTRADA,
                numero_adendum=form.cleaned_data.get('numero_adendum', ''),
                bodega=form.cleaned_data['bodega_destino'],
                descripcion=form.cleaned_data.get('descripcion', ''),
                usuario=request.user
            )
            
            for prod_data in productos:
                try:
                    producto = Producto.objects.get(pk=prod_data['producto_id'])
                    cantidad = int(prod_data['cantidad'])
                    if cantidad <= 0:
                        continue
                    
                    Movimiento.objects.create(
                        tipo=Movimiento.TIPO_ENTRADA,
                        producto=producto,
                        bodega_destino=form.cleaned_data['bodega_destino'],
                        cantidad=cantidad,
                        descripcion=f"Entrada masiva - Boleta: {movimiento_masivo.numero_boleta}",
                        usuario=request.user,
                        movimiento_masivo=movimiento_masivo
                    )
                    
                    inventario, created = Inventario.objects.get_or_create(
                        producto=producto,
                        bodega=form.cleaned_data['bodega_destino'],
                        defaults={'cantidad': 0, 'stock_minimo': producto.stock_minimo}
                    )
                    inventario.cantidad += cantidad
                    inventario.save()
                except (Producto.DoesNotExist, ValueError, KeyError):
                    continue
            
            messages.success(request, f'Entrada masiva registrada. Boleta: {movimiento_masivo.numero_boleta}')
            return redirect('inventario:detalle_movimiento_masivo', pk=movimiento_masivo.pk)
    else:
        form = EntradaMasivaForm()
    
    productos_list = list(Producto.objects.all().order_by('nombre').values(
        'id', 'nombre', 'codigo', 'numero_serie', 'precio'
    ))
    for p in productos_list:
        p['precio'] = str(p['precio'])
        p['numero_serie'] = p['numero_serie'] or ''
    
    context = {
        'form': form,
        'titulo': 'Entrada Masiva',
        'tipo': 'entrada',
        'productos_json': json.dumps(productos_list),
    }
    return render(request, 'inventario/movimiento_masivo_form.html', context)

# ============================================================
# MOVIMIENTOS MASIVOS
# ============================================================


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
            
            # Verificar stock
            errores = []
            for prod_data in productos:
                try:
                    producto = Producto.objects.get(pk=prod_data['producto_id'])
                    cantidad = int(prod_data['cantidad'])
                    
                    inventario = Inventario.objects.filter(
                        producto=producto,
                        bodega=form.cleaned_data['bodega_origen']
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
                bodega=form.cleaned_data['bodega_origen'],
                descripcion=form.cleaned_data.get('descripcion', ''),
                usuario=request.user
            )
            
            for prod_data in productos:
                try:
                    producto = Producto.objects.get(pk=prod_data['producto_id'])
                    cantidad = int(prod_data['cantidad'])
                    if cantidad <= 0:
                        continue
                    
                    Movimiento.objects.create(
                        tipo=Movimiento.TIPO_SALIDA,
                        producto=producto,
                        bodega_origen=form.cleaned_data['bodega_origen'],
                        cantidad=cantidad,
                        descripcion=f"Salida masiva - Boleta: {movimiento_masivo.numero_boleta}",
                        usuario=request.user,
                        movimiento_masivo=movimiento_masivo
                    )
                    
                    inventario = Inventario.objects.get(
                        producto=producto,
                        bodega=form.cleaned_data['bodega_origen']
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
        'id', 'nombre', 'codigo', 'numero_serie', 'precio'
    ))
    for p in productos_list:
        p['precio'] = str(p['precio'])
        p['numero_serie'] = p['numero_serie'] or ''
    
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
    movimientos_detalle = movimiento_masivo.movimientos_detalle.all()
    
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
            
            # Verificar stock en bodega origen
            errores = []
            for prod_data in productos:
                try:
                    producto = Producto.objects.get(pk=prod_data['producto_id'])
                    cantidad = int(prod_data['cantidad'])
                    
                    inventario = Inventario.objects.filter(
                        producto=producto,
                        bodega=form.cleaned_data['bodega_origen']
                    ).first()
                    
                    if not inventario or inventario.cantidad < cantidad:
                        disponible = inventario.cantidad if inventario else 0
                        errores.append(f"{producto.nombre}: stock insuficiente en origen (disponible: {disponible})")
                except (Producto.DoesNotExist, ValueError, KeyError):
                    continue
            
            if errores:
                for error in errores:
                    messages.error(request, error)
                return render(request, 'inventario/movimiento_masivo_form.html', {
                    'form': form, 'titulo': 'Traslado Masivo', 'tipo': 'traslado'
                })
            
            # Crear movimiento masivo
            movimiento_masivo = MovimientoMasivo.objects.create(
                tipo=MovimientoMasivo.TIPO_TRASLADO,
                numero_adendum=form.cleaned_data.get('numero_adendum', ''),
                bodega=form.cleaned_data['bodega_origen'],
                bodega_destino=form.cleaned_data['bodega_destino'],
                descripcion=form.cleaned_data.get('descripcion', ''),
                usuario=request.user
            )
            
            # Procesar cada producto
            for prod_data in productos:
                try:
                    producto = Producto.objects.get(pk=prod_data['producto_id'])
                    cantidad = int(prod_data['cantidad'])
                    if cantidad <= 0:
                        continue
                    
                    # Movimiento individual
                    Movimiento.objects.create(
                        tipo=Movimiento.TIPO_TRASLADO,
                        producto=producto,
                        bodega_origen=form.cleaned_data['bodega_origen'],
                        bodega_destino=form.cleaned_data['bodega_destino'],
                        cantidad=cantidad,
                        descripcion=f"Traslado masivo - Boleta: {movimiento_masivo.numero_boleta}",
                        usuario=request.user,
                        movimiento_masivo=movimiento_masivo
                    )
                    
                    # Restar de bodega origen
                    inv_origen = Inventario.objects.get(
                        producto=producto,
                        bodega=form.cleaned_data['bodega_origen']
                    )
                    inv_origen.cantidad -= cantidad
                    inv_origen.save()
                    
                    # Sumar a bodega destino
                    inv_destino, created = Inventario.objects.get_or_create(
                        producto=producto,
                        bodega=form.cleaned_data['bodega_destino'],
                        defaults={'cantidad': 0, 'stock_minimo': producto.stock_minimo}
                    )
                    inv_destino.cantidad += cantidad
                    inv_destino.save()
                    
                except (Producto.DoesNotExist, Inventario.DoesNotExist, ValueError, KeyError):
                    continue
            
            messages.success(
                request, 
                f'Traslado masivo registrado. Boleta: {movimiento_masivo.numero_boleta}'
            )
            return redirect('inventario:detalle_movimiento_masivo', pk=movimiento_masivo.pk)
    else:
        form = TrasladoMasivoForm()
    
    # Pasar productos como JSON
    productos_list = list(Producto.objects.all().order_by('nombre').values(
        'id', 'nombre', 'codigo', 'numero_serie', 'precio'
    ))
    for p in productos_list:
        p['precio'] = str(p['precio'])
        p['numero_serie'] = p['numero_serie'] or ''
    
    context = {
        'form': form,
        'titulo': 'Traslado Masivo',
        'tipo': 'traslado',
        'productos_json': json.dumps(productos_list),
    }
    return render(request, 'inventario/movimiento_masivo_form.html', context)


@login_required
def generar_pdf_transferencia(request, pk):
    movimiento_masivo = get_object_or_404(MovimientoMasivo, pk=pk)
    movimientos_detalle = movimiento_masivo.movimientos_detalle.all()

    context = {
        'movimiento': movimiento_masivo,
        'movimientos_detalle': movimientos_detalle,
    }

    # Renderiza la plantilla HTML con el contexto
    html_string = render_to_string('inventario/transferencia_pdf.html', context)

    # Crea un buffer en memoria para almacenar el PDF
    buffer = io.BytesIO()
    
    # Convierte el HTML a PDF usando WeasyPrint
    HTML(string=html_string, base_url=request.build_absolute_uri()).write_pdf(buffer)
    
    # Regresa el buffer al principio
    buffer.seek(0)
    
    # Crea la respuesta HTTP con el contenido del PDF
    return FileResponse(buffer, as_attachment=True, filename=f'transferencia_{movimiento_masivo.numero_boleta}.pdf')