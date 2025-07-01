from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta
import re
import math

class RecipeValidator:
    """Validation utilities for recipes"""
    
    @staticmethod
    def validate_gravity(value, field_name="gravity"):
        """Validate gravity readings"""
        if value < 0.990 or value > 1.200:
            raise ValidationError(f"{field_name} must be between 0.990 and 1.200")
        return value
    
    @staticmethod
    def validate_percentage(value, field_name="percentage"):
        """Validate percentage values"""
        if value < 0 or value > 100:
            raise ValidationError(f"{field_name} must be between 0 and 100")
        return value
    
    @staticmethod
    def validate_temperature(value, unit="C"):
        """Validate temperature readings"""
        if unit == "C":
            if value < -10 or value > 110:
                raise ValidationError("Temperature must be between -10°C and 110°C")
        elif unit == "F":
            if value < 14 or value > 230:
                raise ValidationError("Temperature must be between 14°F and 230°F")
        return value

class UnitConverter:
    """Unit conversion utilities"""
    
    # Weight conversions (to kg)
    WEIGHT_CONVERSIONS = {
        'kg': 1.0,
        'g': 0.001,
        'lb': 0.453592,
        'oz': 0.0283495,
        'unit': 1.0,  # Assume 1 unit = 1 kg for calculations
    }
    
    # Temperature conversions
    @staticmethod
    def celsius_to_fahrenheit(celsius):
        """Convert Celsius to Fahrenheit"""
        return (celsius * 9/5) + 32
    
    @staticmethod
    def fahrenheit_to_celsius(fahrenheit):
        """Convert Fahrenheit to Celsius"""
        return (fahrenheit - 32) * 5/9
    
    @classmethod
    def convert_weight(cls, value, from_unit, to_unit):
        """Convert between weight units"""
        if from_unit not in cls.WEIGHT_CONVERSIONS:
            raise ValueError(f"Unknown unit: {from_unit}")
        if to_unit not in cls.WEIGHT_CONVERSIONS:
            raise ValueError(f"Unknown unit: {to_unit}")
        
        # Convert to kg first, then to target unit
        kg_value = value * cls.WEIGHT_CONVERSIONS[from_unit]
        return kg_value / cls.WEIGHT_CONVERSIONS[to_unit]
    
    @staticmethod
    def convert_volume(value, from_unit, to_unit):
        """Convert between volume units"""
        conversions = {
            'L': 1.0,
            'ml': 0.001,
            'gal': 3.78541,
            'qt': 0.946353,
            'pt': 0.473176,
            'fl_oz': 0.0295735,
        }
        
        if from_unit not in conversions:
            raise ValueError(f"Unknown volume unit: {from_unit}")
        if to_unit not in conversions:
            raise ValueError(f"Unknown volume unit: {to_unit}")
        
        liters = value * conversions[from_unit]
        return liters / conversions[to_unit]

class BrewingUtils:
    """Additional brewing calculation utilities"""
    
    @staticmethod
    def calculate_mash_water_ratio(grain_weight_kg, ratio=3.0):
        """Calculate mash water volume based on grain weight and ratio"""
        return grain_weight_kg * ratio
    
    @staticmethod
    def calculate_sparge_water(batch_size, mash_water, grain_absorption=0.96):
        """Calculate sparge water volume for traditional brewing"""
        grain_weight = mash_water / 3.0  # Approximate grain weight
        absorbed_water = grain_weight * grain_absorption
        boil_off = batch_size * 0.15  # Assume 15% boil-off
        
        return batch_size + absorbed_water + boil_off - mash_water
    
    @staticmethod
    def calculate_preboil_volume(batch_size, boil_time_minutes, boil_off_rate=4.0):
        """Calculate pre-boil volume needed"""
        boil_off_percentage = (boil_time_minutes / 60) * (boil_off_rate / 100)
        return batch_size / (1 - boil_off_percentage)
    
    @staticmethod
    def estimate_fermentation_time(style_name, starting_gravity):
        """Estimate fermentation time based on style and gravity"""
        base_days = 7
        
        # Adjust for style
        if 'lager' in style_name.lower():
            base_days += 14  # Lagers take longer
        elif 'wheat' in style_name.lower():
            base_days -= 1  # Wheat beers ferment quickly
        elif 'stout' in style_name.lower() or 'porter' in style_name.lower():
            base_days += 3  # Dark beers may take longer
        
        # Adjust for gravity
        if starting_gravity > 1.065:
            base_days += 3  # High gravity takes longer
        elif starting_gravity < 1.045:
            base_days -= 2  # Low gravity ferments quickly
        
        return max(5, base_days)  # Minimum 5 days
    
    @staticmethod
    def calculate_alcohol_tolerance(yeast_strain):
        """Estimate alcohol tolerance based on yeast strain"""
        tolerances = {
            'US-05': 11.0,
            'S-04': 9.5,
            'WB-06': 8.0,
            'S-23': 10.0,
            'W-34/70': 10.0,
            '1056': 11.0,
            'WLP001': 11.0,
        }
        
        return tolerances.get(yeast_strain, 10.0)  # Default 10%

class RecipeScaler:
    """Scale recipes to different batch sizes"""
    
    @staticmethod
    def scale_recipe(recipe, new_batch_size, scale_hops=True):
        """Scale entire recipe to new batch size"""
        scale_factor = new_batch_size / recipe.batch_size
        
        scaled_data = {
            'grains': [],
            'hops': [],
            'yeast': [],
            'scale_factor': scale_factor
        }
        
        # Scale grains
        for grain_addition in recipe.grainaddition_set.all():
            scaled_data['grains'].append({
                'grain': grain_addition.grain,
                'weight': grain_addition.weight * scale_factor,
                'percentage': grain_addition.percentage
            })
        
        # Scale hops
        for hop_addition in recipe.hopaddition_set.all():
            hop_scale = scale_factor if scale_hops else 1.0
            scaled_data['hops'].append({
                'hop': hop_addition.hop,
                'weight': hop_addition.weight * hop_scale,
                'boil_time': hop_addition.boil_time,
                'use': hop_addition.use
            })
        
        # Scale yeast (less linear scaling)
        for yeast_addition in recipe.yeastaddition_set.all():
            # Yeast scaling is not linear - use square root
            yeast_scale = math.sqrt(scale_factor)
            scaled_data['yeast'].append({
                'yeast': yeast_addition.yeast,
                'amount': max(1.0, yeast_addition.amount * yeast_scale)
            })
        
        return scaled_data

class WaterChemistry:
    """Water chemistry calculations"""
    
    @staticmethod
    def calculate_salt_additions(volume_liters, water_profile, target_profile):
        """Calculate salt additions for water treatment"""
        # This is a simplified version - real water chemistry is complex
        additions = {}
        
        # Calcium Chloride for calcium and chloride
        ca_diff = target_profile.get('calcium', 50) - water_profile.get('calcium', 50)
        if ca_diff > 0:
            additions['calcium_chloride'] = ca_diff * volume_liters * 0.00368  # Simplified calculation
        
        # Gypsum for calcium and sulfate
        so4_diff = target_profile.get('sulfate', 150) - water_profile.get('sulfate', 50)
        if so4_diff > 0:
            additions['gypsum'] = so4_diff * volume_liters * 0.00430  # Simplified calculation
        
        return additions

class InventoryAlerts:
    """Inventory management utilities"""
    
    @staticmethod
    def check_low_stock(user):
        """Check for low stock items"""
        from inventory.models import InventoryItem
        
        low_stock_items = InventoryItem.objects.filter(
            user=user,
            current_stock__lte=models.F('minimum_stock')
        )
        
        return low_stock_items
    
    @staticmethod
    def check_expiring_items(user, days_ahead=30):
        """Check for items expiring soon"""
        from inventory.models import InventoryItem
        
        cutoff_date = timezone.now().date() + timedelta(days=days_ahead)
        
        expiring_items = InventoryItem.objects.filter(
            user=user,
            expiry_date__lte=cutoff_date,
            expiry_date__gte=timezone.now().date()
        )
        
        return expiring_items

def parse_recipe_text(text):
    """Parse recipe text and extract ingredients"""
    # Simple regex patterns for common recipe formats
    grain_pattern = r'(\d+(?:\.\d+)?)\s*(kg|g|lb|oz)\s+(.+?)(?:\n|$)'
    hop_pattern = r'(\d+(?:\.\d+)?)\s*g?\s+(.+?)\s+@?\s*(\d+)\s*min'
    
    grains = []
    hops = []
    
    for match in re.finditer(grain_pattern, text, re.IGNORECASE):
        amount, unit, ingredient = match.groups()
        grains.append({
            'amount': float(amount),
            'unit': unit.lower(),
            'ingredient': ingredient.strip()
        })
    
    for match in re.finditer(hop_pattern, text, re.IGNORECASE):
        amount, ingredient, time = match.groups()
        hops.append({
            'amount': float(amount),
            'ingredient': ingredient.strip(),
            'time': int(time)
        })
    
    return {'grains': grains, 'hops': hops}

def export_recipe_beerxml(recipe):
    """Export recipe to BeerXML format"""
    xml_template = """<?xml version="1.0" encoding="UTF-8"?>
<RECIPES>
<RECIPE>
    <NAME>{name}</NAME>
    <VERSION>1</VERSION>
    <TYPE>All Grain</TYPE>
    <STYLE>
        <NAME>{style}</NAME>
        <VERSION>1</VERSION>
        <CATEGORY>Custom</CATEGORY>
        <CATEGORY_NUMBER>1</CATEGORY_NUMBER>
        <STYLE_LETTER>A</STYLE_LETTER>
        <STYLE_GUIDE>Custom</STYLE_GUIDE>
    </STYLE>
    <BREWER>{brewer}</BREWER>
    <BATCH_SIZE>{batch_size}</BATCH_SIZE>
    <BOIL_SIZE>{boil_size}</BOIL_SIZE>
    <BOIL_TIME>60</BOIL_TIME>
    <EFFICIENCY>{efficiency}</EFFICIENCY>
    <FERMENTABLES>
        {fermentables}
    </FERMENTABLES>
    <HOPS>
        {hops}
    </HOPS>
    <YEASTS>
        {yeasts}
    </YEASTS>
    <NOTES>{notes}</NOTES>
</RECIPE>
</RECIPES>"""
    
    # Build fermentables XML
    fermentables_xml = ""
    for grain in recipe.grainaddition_set.all():
        fermentables_xml += f"""
        <FERMENTABLE>
            <NAME>{grain.grain.name}</NAME>
            <VERSION>1</VERSION>
            <TYPE>Grain</TYPE>
            <AMOUNT>{grain.weight}</AMOUNT>
            <YIELD>{grain.grain.extract_potential}</YIELD>
            <COLOR>{grain.grain.color}</COLOR>
        </FERMENTABLE>"""
    
    # Build hops XML
    hops_xml = ""
    for hop in recipe.hopaddition_set.all():
        hops_xml += f"""
        <HOP>
            <NAME>{hop.hop.name}</NAME>
            <VERSION>1</VERSION>
            <ALPHA>{hop.hop.alpha_acid}</ALPHA>
            <AMOUNT>{hop.weight}</AMOUNT>
            <USE>{hop.use.capitalize()}</USE>
            <TIME>{hop.boil_time}</TIME>
        </HOP>"""
    
    # Build yeasts XML
    yeasts_xml = ""
    for yeast in recipe.yeastaddition_set.all():
        yeasts_xml += f"""
        <YEAST>
            <NAME>{yeast.yeast.name}</NAME>
            <VERSION>1</VERSION>
            <TYPE>{yeast.yeast.yeast_type.capitalize()}</TYPE>
            <FORM>Liquid</FORM>
            <AMOUNT>{yeast.amount}</AMOUNT>
            <ATTENUATION>{yeast.yeast.attenuation}</ATTENUATION>
        </YEAST>"""
    
    return xml_template.format(
        name=recipe.name,
        style=recipe.style.name,
        brewer=recipe.created_by.username,
        batch_size=recipe.batch_size,
        boil_size=recipe.batch_size * 1.2,  # Estimate
        efficiency=recipe.efficiency,
        fermentables=fermentables_xml,
        hops=hops_xml,
        yeasts=yeasts_xml,
        notes=recipe.notes or ""
    )