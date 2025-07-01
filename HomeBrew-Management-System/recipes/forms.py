# recipes/forms.py

from django import forms
from django.forms import modelformset_factory, inlineformset_factory
from .models import Recipe, GrainAddition, HopAddition, YeastAddition, RecipeStep
from core.models import BeerStyle

class RecipeForm(forms.ModelForm):
    class Meta:
        model = Recipe
        fields = ['name', 'description', 'style', 'batch_size', 'efficiency', 'notes', 'is_public', 'is_favorite']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'notes': forms.Textarea(attrs={'rows': 4}),
            'batch_size': forms.NumberInput(attrs={'step': '0.1', 'min': '1'}),
            'efficiency': forms.NumberInput(attrs={'step': '0.1', 'min': '50', 'max': '100'}),
        }

class GrainAdditionForm(forms.ModelForm):
    class Meta:
        model = GrainAddition
        fields = ['grain', 'weight']
        widgets = {
            'weight': forms.NumberInput(attrs={'step': '0.01', 'min': '0.01'}),
        }

class HopAdditionForm(forms.ModelForm):
    class Meta:
        model = HopAddition
        fields = ['hop', 'weight', 'boil_time', 'use']
        widgets = {
            'weight': forms.NumberInput(attrs={'step': '0.001', 'min': '0.001'}),
            'boil_time': forms.NumberInput(attrs={'min': '0'}),
        }

class YeastAdditionForm(forms.ModelForm):
    class Meta:
        model = YeastAddition
        fields = ['yeast', 'amount']
        widgets = {
            'amount': forms.NumberInput(attrs={'step': '0.1', 'min': '0.1'}),
        }

class RecipeGeneratorForm(forms.Form):
    """Form for generating recipes based on style and budget"""
    RECIPE_TYPES = [
        ('simple', 'Simple (3-4 ingredients)'),
        ('moderate', 'Moderate (5-7 ingredients)'),
        ('complex', 'Complex (8+ ingredients)'),
    ]
    
    style = forms.ModelChoiceField(
        queryset=BeerStyle.objects.all(),
        help_text="Select the beer style you want to brew"
    )
    batch_size = forms.FloatField(
        initial=20.0,
        min_value=1.0,
        max_value=1000.0,
        help_text="Batch size in liters"
    )
    max_cost = forms.FloatField(
        required=False,
        min_value=0.0,
        help_text="Maximum cost (leave blank for no limit)"
    )
    complexity = forms.ChoiceField(
        choices=RECIPE_TYPES,
        initial='moderate',
        help_text="Recipe complexity level"
    )
    use_inventory_only = forms.BooleanField(
        required=False,
        initial=False,
        help_text="Only use ingredients from current inventory"
    )

# Create formsets for inline editing
GrainAdditionFormSet = inlineformset_factory(
    Recipe, GrainAddition, form=GrainAdditionForm, extra=1, can_delete=True
)

HopAdditionFormSet = inlineformset_factory(
    Recipe, HopAddition, form=HopAdditionForm, extra=1, can_delete=True
)

YeastAdditionFormSet = inlineformset_factory(
    Recipe, YeastAddition, form=YeastAdditionForm, extra=1, can_delete=True
)