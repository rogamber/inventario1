from django.urls import path
from . import views

app_name = 'inventario'

urlpatterns = [
    # Productos
    path('', views.lista_productos, name='lista_productos'),
    path('producto/<int:pk>/', views.detalle_producto, name='detalle_producto'),
    path('producto/nuevo/', views.crear_producto, name='crear_producto'),
    path('producto/<int:pk>/editar/', views.editar_producto, name='editar_producto'),
    path('producto/<int:pk>/eliminar/', views.eliminar_producto, name='eliminar_producto'),
    
    # Bodegas
    path('bodegas/', views.lista_bodegas, name='lista_bodegas'),
    path('bodega/nuevo/', views.crear_bodega, name='crear_bodega'),
    path('bodega/<int:pk>/editar/', views.editar_bodega, name='editar_bodega'),
    path('bodega/<int:bodega_id>/inventario/', views.inventario_por_bodega, name='inventario_bodega'),
    
    # Movimientos
    path('movimientos/', views.lista_movimientos, name='lista_movimientos'),
    path('movimiento/<int:pk>/', views.detalle_movimiento, name='detalle_movimiento'),
    path('movimiento/entrada/', views.entrada_producto, name='entrada_producto'),
    path('movimiento/salida/', views.salida_producto, name='salida_producto'),
    path('movimiento/traslado/', views.traslado_producto, name='traslado_producto'),
    
    # Movimientos masivos
    path('movimiento/masivo/entrada/', views.entrada_masiva, name='entrada_masiva'),
    path('movimiento/masivo/salida/', views.salida_masiva, name='salida_masiva'),
    path('movimiento/masivo/<int:pk>/', views.detalle_movimiento_masivo, name='detalle_movimiento_masivo'),
    path('movimiento/masivo/traslado/', views.traslado_masivo, name='traslado_masivo'),
    path('movimientos/masivos/', views.lista_movimientos_masivos, name='lista_movimientos_masivos'),
    path('movimiento/masivo/<int:pk>/pdf/', views.generar_pdf_transferencia, name='pdf_transferencia'),

    # Exportar Excel
    path('bodega/<int:bodega_id>/exportar-excel/', views.exportar_bodega_excel, name='exportar_bodega_excel'),
    
    # Resumen
    path('resumen/', views.resumen_inventario, name='resumen_inventario'),

    # Unidades (productos con serie)
    path('producto/<int:producto_id>/unidades/', views.lista_unidades, name='lista_unidades'),
    path('producto/<int:producto_id>/unidad/nueva/', views.crear_unidad, name='crear_unidad'),
    path('producto/<int:producto_id>/unidades/masivas/', views.crear_unidades_masivas, name='crear_unidades_masivas'),
    path('unidad/<int:pk>/editar/', views.editar_unidad, name='editar_unidad'),
    path('unidad/<int:pk>/eliminar/', views.eliminar_unidad, name='eliminar_unidad'),

    #obtener unidades disponibles (AJAX)
    path('api/producto/<int:producto_id>/unidades/', views.obtener_unidades_producto, name='obtener_unidades_producto'),

    # Búsqueda por serie
    path('buscar-serie/', views.buscar_serie, name='buscar_serie'),

    # Salidas masivas (detalle y PDF específicos)
    path('movimiento/masivo/salida/<int:pk>/', views.detalle_salida_masiva, name='detalle_salida_masiva'),
    path('movimiento/masivo/salida/<int:pk>/pdf/', views.generar_pdf_salida, name='generar_pdf_salida'),

    # Equipos instalados
    path('equipos-instalados/', views.lista_equipos_instalados, name='lista_equipos_instalados'),
    path('equipo-instalado/<int:pk>/', views.detalle_equipo_instalado, name='detalle_equipo_instalado'),

    # Clientes
    path('clientes/', views.lista_clientes, name='lista_clientes'),
    path('cliente/nuevo/', views.crear_cliente, name='crear_cliente'),
    path('cliente/<int:pk>/', views.detalle_cliente, name='detalle_cliente'),
    path('cliente/<int:pk>/editar/', views.editar_cliente, name='editar_cliente'),
    path('cliente/<int:pk>/eliminar/', views.eliminar_cliente, name='eliminar_cliente'),

    # Reporte por cliente
    path('reporte/equipos-por-cliente/', views.reporte_equipos_por_cliente, name='reporte_equipos_por_cliente'), 
    path('reporte/cliente/<int:cliente_id>/pdf/', views.generar_pdf_reporte_cliente, name='generar_pdf_reporte_cliente'),
 ]