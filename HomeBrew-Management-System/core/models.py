from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class TimeStampedModel(models.Model):
    """
    Abstract base class that provides self-updating 
    'created_at' and 'updated_at' fields.
    """
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        abstract = True

class UserProfile(TimeStampedModel):
    """
    Extended user profile for brewing preferences
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    preferred_batch_size = models.FloatField(default=20.0, help_text="Preferred batch size in liters")
    brewing_efficiency = models.FloatField(default=75.0, help_text="Average brewing efficiency %")
    equipment_notes = models.TextField(blank=True, help_text="Notes about your brewing equipment")
    
    def __str__(self):
        return f"{self.user.username}'s Profile"

class BeerStyle(TimeStampedModel):
    """
    Beer style definitions (BJCP styles)
    """
    name = models.CharField(max_length=100)
    style_code = models.CharField(max_length=10, unique=True)
    description = models.TextField()
    
    # Style ranges
    og_min = models.FloatField(help_text="Original Gravity minimum")
    og_max = models.FloatField(help_text="Original Gravity maximum")
    fg_min = models.FloatField(help_text="Final Gravity minimum")  
    fg_max = models.FloatField(help_text="Final Gravity maximum")
    ibu_min = models.IntegerField(help_text="IBU minimum")
    ibu_max = models.IntegerField(help_text="IBU maximum")
    srm_min = models.IntegerField(help_text="SRM color minimum")
    srm_max = models.IntegerField(help_text="SRM color maximum")
    abv_min = models.FloatField(help_text="ABV minimum")
    abv_max = models.FloatField(help_text="ABV maximum")
    
    class Meta:
        ordering = ['style_code']
    
    def __str__(self):
        return f"{self.style_code} - {self.name}"

class BrewingCalculator:
    """
    Utility class for brewing calculations
    """
    
    @staticmethod
    def sg_to_plato(sg):
        """Convert Specific Gravity to Plato"""
        return ((sg - 1) * 1000) / 4
    
    @staticmethod
    def plato_to_sg(plato):
        """Convert Plato to Specific Gravity"""
        return (plato * 4 / 1000) + 1
    
    @staticmethod
    def calculate_abv(og, fg):
        """Calculate ABV from Original and Final Gravity"""
        return (og - fg) * 131.25
    
    @staticmethod
    def calculate_attenuation(og, fg):
        """Calculate apparent attenuation"""
        return ((og - fg) / (og - 1)) * 100
    
    @staticmethod
    def calculate_strike_water_temp(grain_temp, mash_temp, water_ratio):
        """
        Calculate strike water temperature for BIAB
        grain_temp: Temperature of grain in Celsius
        mash_temp: Target mash temperature in Celsius
        water_ratio: Water to grain ratio (L/kg)
        """
        return ((0.2 / water_ratio) * (mash_temp - grain_temp)) + mash_temp
    
    @staticmethod
    def calculate_grain_absorption(grain_weight_kg):
        """
        Calculate water absorbed by grain (BIAB specific)
        Returns absorption in liters
        """
        return grain_weight_kg * 0.96  # 0.96L per kg of grain
    
    @staticmethod
    def calculate_boil_off(boil_time_minutes, boil_off_rate=4.0):
        """
        Calculate boil-off volume
        boil_off_rate: % per hour (default 4%)
        """
        return (boil_time_minutes / 60) * boil_off_rate
    
    @staticmethod
    def calculate_ibu_tinseth(alpha_acid, hop_weight_grams, boil_time_minutes, 
                             batch_size_liters, og):
        """
        Calculate IBU using Tinseth formula
        """
        utilization = (1.65 * (0.000125 ** (og - 1))) * \
                     ((1 - 2.718 ** (-0.04 * boil_time_minutes)) / 4.15)
        
        ibu = (alpha_acid * hop_weight_grams * utilization * 1000) / \
              (batch_size_liters * 100)
        
        return ibu
    
    @staticmethod
    def calculate_srm_color(grain_weights_and_colors):
        """
        Calculate SRM color
        grain_weights_and_colors: list of tuples (weight_kg, color_srm)
        """
        total_mcu = sum(weight * color for weight, color in grain_weights_and_colors)
        return 1.4922 * (total_mcu ** 0.6859)
    
    @staticmethod
    def calculate_extract_points(grain_weight_kg, extract_potential, efficiency):
        """
        Calculate gravity points from grain
        extract_potential: Points per pound per gallon (PPG)
        efficiency: Brewing efficiency as decimal (0.75 for 75%)
        """
        # Convert to metric: 1 kg = 2.2 lbs, 1 liter = 0.264 gallons
        points = (grain_weight_kg * 2.2 * extract_potential * efficiency) / 0.264
        return points