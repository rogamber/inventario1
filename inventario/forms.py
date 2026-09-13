from django import forms
from .models import (
    Producto, Movimiento, Bodega, Inventario, Categoria,
    MovimientoMasivo, Unidad, EstadoUnidad , Cliente
)

class ProductoForm(forms.ModelForm):
    cantidad_inicial = forms.IntegerField(
        min_value=0,
        initial=0,
        required=False,
        label='Cantidad inicial',
        help_text='Solo para productos que NO manejan número de serie'
    )
    bodega_inicial = forms.ModelChoiceField(
        queryset=Bodega.objects.filter(activa=True),
        required=False,
        label='Bodega',
        empty_label='--- Seleccione una bodega ---'
    )
    
    class Meta:
        model = Producto
        fields = [
            'nombre', 'descripcion', 'categoria', 'precio',
            'precio_costo', 'codigo', 'maneja_serie', 'stock_minimo'
        ]
        widgets = {
            'descripcion': forms.Textarea(attrs={'rows': 3}),
            'maneja_serie': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
                'style': 'transform: scale(1.5); margin-right: 10px;'
            }),
        }
        labels = {
            'maneja_serie': '¿Maneja número de serie?',
        }
        help_texts = {
            'maneja_serie': 'Marcar si cada unidad física tiene un número de serie único.',
        }

class MovimientoForm(forms.ModelForm):
    class Meta:
        model = Movimiento
        fields = ['producto', 'bodega_origen', 'bodega_destino', 'cantidad', 'numero_adendum', 'descripcion']
        widgets = {
            'descripcion': forms.Textarea(attrs={'rows': 2}),
            'numero_adendum': forms.TextInput(attrs={
                'placeholder': 'Ej: ADM-2024-001',
                'class': 'form-control'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['bodega_origen'].queryset = Bodega.objects.filter(activa=True)
        self.fields['bodega_destino'].queryset = Bodega.objects.filter(activa=True)
        self.fields['numero_adendum'].required = False


class EntradaForm(MovimientoForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.tipo_movimiento = Movimiento.TIPO_ENTRADA
        self.fields['bodega_origen'].widget = forms.HiddenInput()
        self.fields['bodega_destino'].label = 'Bodega de destino'
        del self.fields['bodega_origen']


class SalidaForm(MovimientoForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.tipo_movimiento = Movimiento.TIPO_SALIDA
        self.fields['bodega_destino'].widget = forms.HiddenInput()
        self.fields['bodega_origen'].label = 'Bodega de origen'
        self.fields['numero_adendum'].required = True
        self.fields['numero_adendum'].label = 'Número de Adendum'
        self.fields['numero_adendum'].help_text = 'Número del adendum que justifica esta salida'
        del self.fields['bodega_destino']
    
    def clean_numero_adendum(self):
        adendum = self.cleaned_data.get('numero_adendum')
        if not adendum:
            raise forms.ValidationError('El número de adendum es obligatorio para las salidas.')
        return adendum


class TrasladoForm(MovimientoForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.tipo_movimiento = Movimiento.TIPO_TRASLADO
        self.fields['bodega_origen'].label = 'Bodega de origen'
        self.fields['bodega_destino'].label = 'Bodega de destino'


class InventarioForm(forms.ModelForm):
    class Meta:
        model = Inventario
        fields = ['producto', 'bodega', 'cantidad', 'stock_minimo']


# ============================================================
# MOVIMIENTOS MASIVOS
# ============================================================

class MovimientoMasivoForm(forms.Form):
    """Formulario para registrar movimientos masivos"""
    producto = forms.ModelChoiceField(
        queryset=Producto.objects.all(),
        label='Producto',
        widget=forms.Select(attrs={'class': 'form-control producto-select'})
    )
    cantidad = forms.IntegerField(
        min_value=1,
        label='Cantidad',
        widget=forms.NumberInput(attrs={'class': 'form-control cantidad-input', 'min': 1})
    )
    numero_serie = forms.CharField(
        max_length=100,
        required=False,
        label='N° Serie (Opcional)',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Opcional'})
    )


class EntradaMasivaForm(forms.Form):
    bodega_destino = forms.ModelChoiceField(
        queryset=Bodega.objects.filter(activa=True),
        label='Bodega de destino',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    numero_adendum = forms.CharField(
        max_length=50,
        required=False,
        label='N° Adendum (Opcional)',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Opcional'})
    )
    descripcion = forms.CharField(
        required=False,
        label='Descripción',
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2})
    )


class SalidaMasivaForm(forms.Form):
    bodega_origen = forms.ModelChoiceField(
        queryset=Bodega.objects.filter(activa=True),
        label='Bodega de origen',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    cliente = forms.ModelChoiceField(  # ← NUEVO
        queryset=Cliente.objects.filter(activo=True),
        label='Cliente',
        required=True,
        widget=forms.Select(attrs={'class': 'form-control'}),
        empty_label='--- Seleccione un cliente ---'
    )
    numero_adendum = forms.CharField(
        max_length=50,
        required=True,
        label='N° Adendum',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Obligatorio'})
    )
    descripcion = forms.CharField(
        required=False,
        label='Descripción',
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2})
    )


class TrasladoMasivoForm(forms.Form):
    bodega_origen = forms.ModelChoiceField(
        queryset=Bodega.objects.filter(activa=True),
        label='Bodega de origen',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    bodega_destino = forms.ModelChoiceField(
        queryset=Bodega.objects.filter(activa=True),
        label='Bodega de destino',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    numero_adendum = forms.CharField(
        max_length=50,
        required=False,
        label='N° Adendum (Opcional)',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Opcional'})
    )
    descripcion = forms.CharField(
        required=False,
        label='Descripción',
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2})
    )
    
    def clean(self):
        cleaned_data = super().clean()
        origen = cleaned_data.get('bodega_origen')
        destino = cleaned_data.get('bodega_destino')
        
        if origen and destino and origen == destino:
            raise forms.ValidationError('Las bodegas de origen y destino deben ser diferentes.')
        
        return cleaned_data



# ============================================================
# UNIDADES (productos con número de serie)
# ============================================================

class UnidadForm(forms.ModelForm):
    class Meta:
        model = Unidad
        fields = ['numero_serie', 'bodega', 'estado', 'notas']
        widgets = {
            'numero_serie': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej: SN-2024-001'
            }),
            'notas': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            'bodega': forms.Select(attrs={'class': 'form-control'}),
            'estado': forms.Select(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Solo mostrar estados activos
        self.fields['estado'].queryset = EstadoUnidad.objects.filter(activo=True)

class UnidadMasivaForm(forms.Form):
    """Formulario para agregar varias unidades de una vez"""
    cantidad = forms.IntegerField(
        min_value=1,
        initial=1,
        label='Cantidad de unidades',
        widget=forms.NumberInput(attrs={'class': 'form-control', 'min': 1})
    )
    prefijo = forms.CharField(
        max_length=50,
        required=False,
        label='Prefijo del número de serie',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ej: SN-2024- (opcional)'
        })
    )
    numero_inicial = forms.IntegerField(
        min_value=1,
        initial=1,
        label='Número inicial',
        widget=forms.NumberInput(attrs={'class': 'form-control', 'min': 1})
    )
    bodega = forms.ModelChoiceField(
        queryset=Bodega.objects.filter(activa=True),
        label='Bodega',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    estado = forms.ModelChoiceField(  # ← Cambio: ModelChoiceField en lugar de ChoiceField
        queryset=EstadoUnidad.objects.filter(activo=True),
        label='Estado',
        widget=forms.Select(attrs={'class': 'form-control'})
    )

class ClienteForm(forms.ModelForm):  # ← NUEVO
    class Meta:
        model = Cliente
        fields = ['nombre', 'cedula', 'contacto', 'telefono', 'email', 'direccion', 'notas', 'activo']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'cedula': forms.TextInput(attrs={'class': 'form-control'}),
            'contacto': forms.TextInput(attrs={'class': 'form-control'}),
            'telefono': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'direccion': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'notas': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

