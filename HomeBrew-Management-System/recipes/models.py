from django.db import models
from django.contrib.auth.models import User
from django.urls import reverse
from django.core.validators import MinValueValidator, MaxValueValidator
from core.models import TimeStampedModel, BeerStyle, BrewingCalculator
import json

class Recipe(TimeStampedModel):
    """
    Main recipe model
    """
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    style = models.ForeignKey(BeerStyle, on_delete=models.CASCADE)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    
    # Batch information
    batch_size = models.FloatField(help_text="Batch size in liters")
    efficiency = models.FloatField(default=75.0, help_text="Expected efficiency %")
    
    # Calculated values (updated when ingredients change)
    calculated_og = models.FloatField(null=True, blank=True)
    calculated_fg = models.FloatField(null=True, blank=True)
    calculated_ibu = models.FloatField(null=True, blank=True)
    calculated_srm = models.FloatField(null=True, blank=True)
    calculated_abv = models.FloatField(null=True, blank=True)
    
    # Recipe status
    is_public = models.BooleanField(default=False)
    is_favorite = models.BooleanField(default=False)
    
    # Brewing notes
    notes = models.TextField(blank=True, help_text="General brewing notes")
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return self.name
    
    def get_absolute_url(self):
        return reverse('recipe_detail', kwargs={'pk': self.pk})
    
    def total_grain_weight(self):
        """Calculate total grain weight in kg"""
        return sum(ingredient.weight for ingredient in self.grainaddition_set.all())
    
    def total_cost(self):
        """Calculate total recipe cost"""
        grain_cost = sum(addition.cost() for addition in self.grainaddition_set.all())
        hop_cost = sum(addition.cost() for addition in self.hopaddition_set.all())
        yeast_cost = sum(addition.cost() for addition in self.yeastaddition_set.all())
        return grain_cost + hop_cost + yeast_cost
    
    def calculate_all_values(self):
        """Recalculate all recipe values"""
        # Original Gravity calculation
        total_points = 0
        grain_colors = []
        
        for grain_addition in self.grainaddition_set.all():
            points = BrewingCalculator.calculate_extract_points(
                grain_addition.weight, 
                grain_addition.grain.extract_potential,
                self.efficiency / 100
            )
            total_points += points
            grain_colors.append((grain_addition.weight, grain_addition.grain.color))
        
        if total_points > 0:
            self.calculated_og = 1 + (total_points / self.batch_size / 1000)
        else:
            self.calculated_og = 1.000
        
        # Final Gravity (rough estimate)
        if self.yeastaddition_set.exists():
            avg_attenuation = sum(y.yeast.attenuation for y in self.yeastaddition_set.all()) / self.yeastaddition_set.count()
            self.calculated_fg = self.calculated_og - ((self.calculated_og - 1) * avg_attenuation / 100)
        else:
            self.calculated_fg = self.calculated_og - 0.010  # Default attenuation
        
        # ABV calculation
        self.calculated_abv = BrewingCalculator.calculate_abv(self.calculated_og, self.calculated_fg)
        
        # IBU calculation
        total_ibu = 0
        for hop_addition in self.hopaddition_set.all():
            ibu = BrewingCalculator.calculate_ibu_tinseth(
                hop_addition.hop.alpha_acid,
                hop_addition.weight * 1000,  # Convert to grams
                hop_addition.boil_time,
                self.batch_size,
                self.calculated_og
            )
            total_ibu += ibu
        self.calculated_ibu = total_ibu
        
        # SRM Color calculation
        if grain_colors:
            self.calculated_srm = BrewingCalculator.calculate_srm_color(grain_colors)
        else:
            self.calculated_srm = 0
        
        self.save()

class Grain(TimeStampedModel):
    """
    Grain/Malt ingredients
    """
    GRAIN_TYPES = [
        ('base', 'Base Malt'),
        ('specialty', 'Specialty Malt'),
        ('crystal', 'Crystal/Caramel'),
        ('roasted', 'Roasted'),
        ('adjunct', 'Adjunct'),
    ]
    
    name = models.CharField(max_length=100)
    grain_type = models.CharField(max_length=20, choices=GRAIN_TYPES)
    color = models.IntegerField(help_text="Color in SRM")
    extract_potential = models.FloatField(help_text="Extract potential (PPG)")
    description = models.TextField(blank=True)
    
    class Meta:
        ordering = ['grain_type', 'name']
    
    def __str__(self):
        return f"{self.name} ({self.color} SRM)"

class Hop(TimeStampedModel):
    """
    Hop ingredients
    """
    HOP_TYPES = [
        ('bittering', 'Bittering'),
        ('aroma', 'Aroma'),
        ('dual', 'Dual Purpose'),
    ]
    
    name = models.CharField(max_length=100)
    hop_type = models.CharField(max_length=20, choices=HOP_TYPES)
    alpha_acid = models.FloatField(help_text="Alpha acid percentage")
    description = models.TextField(blank=True)
    
    class Meta:
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} ({self.alpha_acid}% AA)"

class Yeast(TimeStampedModel):
    """
    Yeast strains
    """
    YEAST_TYPES = [
        ('ale', 'Ale'),
        ('lager', 'Lager'),
        ('wild', 'Wild/Brett'),
        ('wheat', 'Wheat'),
    ]
    
    name = models.CharField(max_length=100)
    laboratory = models.CharField(max_length=50)
    strain_number = models.CharField(max_length=20)
    yeast_type = models.CharField(max_length=20, choices=YEAST_TYPES)
    attenuation = models.FloatField(help_text="Typical attenuation %")
    temp_range_min = models.IntegerField(help_text="Min temperature °C")
    temp_range_max = models.IntegerField(help_text="Max temperature °C")
    description = models.TextField(blank=True)
    
    class Meta:
        ordering = ['laboratory', 'strain_number']
    
    def __str__(self):
        return f"{self.laboratory} {self.strain_number} - {self.name}"

class GrainAddition(TimeStampedModel):
    """
    Grain addition to a recipe
    """
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE)
    grain = models.ForeignKey(Grain, on_delete=models.CASCADE)
    weight = models.FloatField(help_text="Weight in kg")
    percentage = models.FloatField(blank=True, null=True, help_text="Percentage of grain bill")
    
    class Meta:
        ordering = ['-weight']
    
    def __str__(self):
        return f"{self.weight}kg {self.grain.name}"
    
    def cost(self):
        """Calculate cost of this grain addition"""
        try:
            from inventory.models import InventoryItem
            inventory_item = InventoryItem.objects.get(
                ingredient_type='grain',
                ingredient_id=self.grain.id
            )
            return (self.weight * inventory_item.cost_per_kg)
        except:
            return 0.0

class HopAddition(TimeStampedModel):
    """
    Hop addition to a recipe
    """
    HOP_USES = [
        ('boil', 'Boil'),
        ('flameout', 'Flameout'),
        ('dry_hop', 'Dry Hop'),
        ('whirlpool', 'Whirlpool'),
    ]
    
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE)
    hop = models.ForeignKey(Hop, on_delete=models.CASCADE)
    weight = models.FloatField(help_text="Weight in kg")
    boil_time = models.IntegerField(default=0, help_text="Boil time in minutes")
    use = models.CharField(max_length=20, choices=HOP_USES, default='boil')
    
    class Meta:
        ordering = ['-boil_time', '-weight']
    
    def __str__(self):
        return f"{self.weight*1000}g {self.hop.name} @ {self.boil_time}min"
    
    def cost(self):
        """Calculate cost of this hop addition"""
        try:
            from inventory.models import InventoryItem
            inventory_item = InventoryItem.objects.get(
                ingredient_type='hop',
                ingredient_id=self.hop.id
            )
            return (self.weight * inventory_item.cost_per_kg)
        except:
            return 0.0

class YeastAddition(TimeStampedModel):
    """
    Yeast addition to a recipe
    """
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE)
    yeast = models.ForeignKey(Yeast, on_delete=models.CASCADE)
    amount = models.FloatField(help_text="Amount (packets/vials)")
    
    def __str__(self):
        return f"{self.amount} x {self.yeast.name}"
    
    def cost(self):
        """Calculate cost of this yeast addition"""
        try:
            from inventory.models import InventoryItem
            inventory_item = InventoryItem.objects.get(
                ingredient_type='yeast',
                ingredient_id=self.yeast.id
            )
            return (self.amount * inventory_item.cost_per_unit)
        except:
            return 0.0

class RecipeStep(TimeStampedModel):
    """
    Brewing steps for a recipe
    """
    STEP_TYPES = [
        ('mash', 'Mash'),
        ('boil', 'Boil'),
        ('fermentation', 'Fermentation'),
        ('packaging', 'Packaging'),
        ('other', 'Other'),
    ]
    
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE)
    step_type = models.CharField(max_length=20, choices=STEP_TYPES)
    order = models.IntegerField()
    name = models.CharField(max_length=200)
    description = models.TextField()
    duration = models.IntegerField(null=True, blank=True, help_text="Duration in minutes")
    temperature = models.IntegerField(null=True, blank=True, help_text="Temperature in °C")
    
    class Meta:
        ordering = ['order']
    
    def __str__(self):
        return f"{self.recipe.name} - Step {self.order}: {self.name}"