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
    
    # Resumen
    path('resumen/', views.resumen_inventario, name='resumen_inventario'),
]