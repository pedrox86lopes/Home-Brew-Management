from django.db import models
from django.contrib.auth.models import User
from django.db.models import Avg, Count, Sum, Max, Min
from django.utils import timezone
from datetime import timedelta
from core.models import TimeStampedModel

class BrewingStats(models.Model):
    """
    Aggregate brewing statistics for analytics
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    
    # Brewing totals
    total_brews = models.IntegerField(default=0)
    total_batches_liters = models.FloatField(default=0.0)
    successful_brews = models.IntegerField(default=0)
    failed_brews = models.IntegerField(default=0)
    
    # Efficiency stats
    avg_efficiency = models.FloatField(null=True, blank=True)
    best_efficiency = models.FloatField(null=True, blank=True)
    worst_efficiency = models.FloatField(null=True, blank=True)
    
    # Gravity stats
    avg_og = models.FloatField(null=True, blank=True)
    avg_fg = models.FloatField(null=True, blank=True)
    avg_abv = models.FloatField(null=True, blank=True)
    
    # Cost stats
    total_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    avg_cost_per_liter = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    # Timing stats
    avg_brew_time_hours = models.FloatField(null=True, blank=True)
    avg_fermentation_days = models.FloatField(null=True, blank=True)
    
    # Last updated
    last_updated = models.DateTimeField(auto_now=True)
    
    def update_stats(self):
        """Recalculate all statistics"""
        from brewing.models import BrewSession
        from recipes.models import Recipe
        
        # Get all completed brew sessions
        sessions = BrewSession.objects.filter(
            brewer=self.user,
            status='completed'
        )
        
        self.total_brews = sessions.count()
        self.total_batches_liters = sessions.aggregate(
            total=Sum('actual_batch_size')
        )['total'] or 0
        
        # Efficiency stats
        efficiency_stats = sessions.filter(
            actual_efficiency__isnull=False
        ).aggregate(
            avg=Avg('actual_efficiency'),
            max=Max('actual_efficiency'),
            min=Min('actual_efficiency')
        )
        
        self.avg_efficiency = efficiency_stats['avg']
        self.best_efficiency = efficiency_stats['max']
        self.worst_efficiency = efficiency_stats['min']
        
        # Gravity and ABV stats
        gravity_stats = sessions.filter(
            actual_og__isnull=False,
            actual_fg__isnull=False,
            actual_abv__isnull=False
        ).aggregate(
            avg_og=Avg('actual_og'),
            avg_fg=Avg('actual_fg'),
            avg_abv=Avg('actual_abv')
        )
        
        self.avg_og = gravity_stats['avg_og']
        self.avg_fg = gravity_stats['avg_fg']
        self.avg_abv = gravity_stats['avg_abv']
        
        # Cost stats (from recipes)
        user_recipes = Recipe.objects.filter(created_by=self.user)
        if user_recipes.exists():
            total_recipe_cost = sum(recipe.total_cost() for recipe in user_recipes)
            self.total_cost = total_recipe_cost
            
            if self.total_batches_liters > 0:
                self.avg_cost_per_liter = total_recipe_cost / self.total_batches_liters
        
        # Timing stats
        fermentation_sessions = sessions.filter(
            fermentation_start__isnull=False,
            fermentation_end__isnull=False
        )
        
        if fermentation_sessions.exists():
            total_fermentation_time = sum(
                (session.fermentation_end - session.fermentation_start).days
                for session in fermentation_sessions
            )
            self.avg_fermentation_days = total_fermentation_time / fermentation_sessions.count()
        
        self.save()
    
    def success_rate(self):
        """Calculate success rate percentage"""
        if self.total_brews == 0:
            return 0
        return (self.successful_brews / self.total_brews) * 100
