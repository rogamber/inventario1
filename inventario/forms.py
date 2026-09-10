# inventario/forms.py
from django import forms
from .models import Producto, Movimiento, Bodega, Inventario, Categoria


class ProductoForm(forms.ModelForm):
    cantidad_inicial = forms.IntegerField(
        min_value=0,
        initial=0,
        required=False,
        label='Cantidad inicial'
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
            'precio_costo', 'codigo', 'numero_serie', 'stock_minimo'  # <--- Agregar numero_serie
        ]
        widgets = {
            'descripcion': forms.Textarea(attrs={'rows': 3}),
            'numero_serie': forms.TextInput(attrs={
                'placeholder': 'Opcional - Ej: SN-12345-ABC'
            }),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        cantidad = cleaned_data.get('cantidad_inicial')
        bodega = cleaned_data.get('bodega_inicial')
        
        if cantidad and cantidad > 0 and not bodega:
            raise forms.ValidationError('Si ingresas una cantidad inicial, debes seleccionar una bodega.')
        
        return cleaned_data


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
        self.fields['numero_adendum'].required = True  # <--- Obligatorio para salidas
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
    numero_serie = forms.CharField(  # <--- NUEVO
        max_length=100,
        required=False,
        label='N° Serie (Opcional)',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Opcional'})
    )


class EntradaMasivaForm(forms.Form):
    """Formulario principal para entrada masiva"""
    
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
    """Formulario principal para salida masiva"""
    
    bodega_origen = forms.ModelChoiceField(
        queryset=Bodega.objects.filter(activa=True),
        label='Bodega de origen',
        widget=forms.Select(attrs={'class': 'form-control'})
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
    """Formulario principal para traslado masivo"""
    
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