from django.db import models
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from core.models import TimeStampedModel
from recipes.models import Recipe

class BrewSession(TimeStampedModel):
    """
    Active brewing session
    """
    BREW_STATUSES = [
        ('planning', 'Planning'),
        ('active', 'Active Brewing'),
        ('fermenting', 'Fermenting'),
        ('conditioning', 'Conditioning'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    
    CURRENT_STAGES = [
        ('preparation', 'Preparation'),
        ('mashing', 'Mashing'),
        ('sparging', 'Sparging'),
        ('boiling', 'Boiling'),
        ('cooling', 'Cooling'),
        ('fermentation', 'Fermentation'),
        ('secondary', 'Secondary Fermentation'),
        ('conditioning', 'Conditioning'),
        ('packaging', 'Packaging'),
        ('completed', 'Completed'),
    ]
    
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE)
    brewer = models.ForeignKey(User, on_delete=models.CASCADE)
    
    # Session info
    batch_name = models.CharField(max_length=200)
    brew_date = models.DateTimeField(default=timezone.now)
    status = models.CharField(max_length=20, choices=BREW_STATUSES, default='planning')
    current_stage = models.CharField(max_length=20, choices=CURRENT_STAGES, default='preparation')
    
    # Actual measurements
    actual_batch_size = models.FloatField(null=True, blank=True, help_text="Actual batch size in liters")
    actual_og = models.FloatField(null=True, blank=True, help_text="Actual Original Gravity")
    actual_fg = models.FloatField(null=True, blank=True, help_text="Actual Final Gravity")
    actual_abv = models.FloatField(null=True, blank=True, help_text="Actual ABV")
    
    # Efficiency
    actual_efficiency = models.FloatField(null=True, blank=True, help_text="Actual brewing efficiency %")
    
    # Dates
    fermentation_start = models.DateTimeField(null=True, blank=True)
    fermentation_end = models.DateTimeField(null=True, blank=True)
    packaging_date = models.DateTimeField(null=True, blank=True)
    
    # General notes
    notes = models.TextField(blank=True)
    public_notes = models.TextField(blank=True, help_text="Notes to share publicly")
    
    # Files
    photo = models.ImageField(upload_to='brew_sessions/', blank=True)
    
    class Meta:
        ordering = ['-brew_date']
    
    def __str__(self):
        return f"{self.batch_name} - {self.recipe.name}"
    
    def get_absolute_url(self):
        return reverse('brew_session_detail', kwargs={'pk': self.pk})
    
    @property
    def days_since_start(self):
        """Calculate days since brewing started"""
        return (timezone.now() - self.brew_date).days
    
    @property
    def days_fermenting(self):
        """Calculate days fermenting"""
        if self.fermentation_start:
            end_date = self.fermentation_end or timezone.now()
            return (end_date - self.fermentation_start).days
        return 0
    
    @property
    def is_active(self):
        """Check if session is currently active"""
        return self.status in ['active', 'fermenting', 'conditioning']
    
    @property
    def is_fermenting(self):
        """Check if currently fermenting"""
        return self.status == 'fermenting'
    
    @property
    def estimated_fermentation_end(self):
        """Estimate when fermentation will be complete"""
        if self.fermentation_start and not self.fermentation_end:
            # Estimate 14 days for ales, 21 days for lagers
            days = 14 if 'ale' in self.recipe.style.name.lower() else 21
            return self.fermentation_start + timedelta(days=days)
        return None
    
    def get_current_temperature_reading(self):
        """Get latest temperature reading"""
        return self.temperaturereading_set.order_by('-timestamp').first()
    
    def get_current_gravity_reading(self):
        """Get latest gravity reading"""
        return self.gravityreading_set.order_by('-timestamp').first()
    
    def get_fermentation_progress(self):
        """Calculate fermentation progress percentage"""
        if not self.actual_og or not self.fermentation_start:
            return 0
        
        latest_gravity = self.get_current_gravity_reading()
        if not latest_gravity:
            return 0
            
        # Calculate attenuation progress
        target_fg = self.recipe.calculated_fg or (self.actual_og - 0.010)
        current_attenuation = ((self.actual_og - latest_gravity.gravity) / (self.actual_og - 1)) * 100
        target_attenuation = ((self.actual_og - target_fg) / (self.actual_og - 1)) * 100
        
        if target_attenuation > 0:
            return min(100, (current_attenuation / target_attenuation) * 100)
        return 0

class BrewStepLog(TimeStampedModel):
    """
    Log of brewing steps and timings
    """
    brew_session = models.ForeignKey(BrewSession, on_delete=models.CASCADE)
    step_name = models.CharField(max_length=200)
    step_type = models.CharField(max_length=50, choices=[
        ('mash', 'Mash Step'),
        ('boil', 'Boil Addition'),
        ('temperature', 'Temperature Change'),
        ('transfer', 'Transfer'),
        ('measurement', 'Measurement'),
        ('note', 'General Note'),
    ])
    
    start_time = models.DateTimeField(default=timezone.now)
    end_time = models.DateTimeField(null=True, blank=True)
    duration_minutes = models.IntegerField(null=True, blank=True)
    
    target_temperature = models.FloatField(null=True, blank=True, help_text="Target temp in °C")
    actual_temperature = models.FloatField(null=True, blank=True, help_text="Actual temp in °C")
    
    notes = models.TextField(blank=True)
    is_completed = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['start_time']
    
    def __str__(self):
        return f"{self.brew_session.batch_name} - {self.step_name}"
    
    def complete_step(self):
        """Mark step as completed and calculate duration"""
        self.end_time = timezone.now()
        self.duration_minutes = int((self.end_time - self.start_time).total_seconds() / 60)
        self.is_completed = True
        self.save()

class TemperatureReading(TimeStampedModel):
    """
    Temperature readings during brewing and fermentation
    """
    brew_session = models.ForeignKey(BrewSession, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(default=timezone.now)
    temperature = models.FloatField(help_text="Temperature in °C")
    reading_type = models.CharField(max_length=20, choices=[
        ('mash', 'Mash Temperature'),
        ('boil', 'Boil Temperature'),
        ('fermentation', 'Fermentation Temperature'),
        ('ambient', 'Ambient Temperature'),
    ], default='fermentation')
    notes = models.CharField(max_length=200, blank=True)
    
    class Meta:
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"{self.brew_session.batch_name} - {self.temperature}°C"

class GravityReading(TimeStampedModel):
    """
    Gravity readings throughout the brewing process
    """
    brew_session = models.ForeignKey(BrewSession, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(default=timezone.now)
    gravity = models.FloatField(help_text="Specific Gravity")
    reading_type = models.CharField(max_length=20, choices=[
        ('original', 'Original Gravity'),
        ('final', 'Final Gravity'),
        ('progress', 'Fermentation Progress'),
    ])
    temperature = models.FloatField(null=True, blank=True, help_text="Sample temperature °C")
    notes = models.CharField(max_length=200, blank=True)
    
    class Meta:
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"{self.brew_session.batch_name} - SG {self.gravity}"
    
    @property
    def corrected_gravity(self):
        """Temperature-corrected gravity (simplified)"""
        if self.temperature and self.temperature != 20:
            # Simple temperature correction (more complex formulas exist)
            correction = (self.temperature - 20) * 0.0001
            return self.gravity + correction
        return self.gravity

class BrewTimer(TimeStampedModel):
    """
    Active timers for brewing steps
    """
    brew_session = models.ForeignKey(BrewSession, on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    duration_minutes = models.IntegerField()
    start_time = models.DateTimeField(default=timezone.now)
    is_active = models.BooleanField(default=True)
    alert_sent = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['start_time']
    
    def __str__(self):
        return f"{self.name} - {self.duration_minutes}min"
    
    @property
    def time_remaining(self):
        """Calculate time remaining in minutes"""
        if not self.is_active:
            return 0
        
        elapsed = timezone.now() - self.start_time
        elapsed_minutes = elapsed.total_seconds() / 60
        remaining = self.duration_minutes - elapsed_minutes
        return max(0, remaining)
    
    @property
    def is_finished(self):
        """Check if timer is finished"""
        return self.time_remaining <= 0
    
    def stop_timer(self):
        """Stop the timer"""
        self.is_active = False
        self.save()

class FermentationNote(TimeStampedModel):
    """
    Notes and observations during fermentation
    """
    brew_session = models.ForeignKey(BrewSession, on_delete=models.CASCADE)
    note_date = models.DateTimeField(default=timezone.now)
    title = models.CharField(max_length=200)
    content = models.TextField()
    is_public = models.BooleanField(default=False)
    
    # Observation fields
    krausen_activity = models.CharField(max_length=50, choices=[
        ('none', 'No Activity'),
        ('light', 'Light Activity'),
        ('moderate', 'Moderate Activity'),
        ('vigorous', 'Vigorous Activity'),
        ('peaked', 'Peaked'),
        ('falling', 'Falling'),
    ], null=True, blank=True)
    
    aroma_notes = models.TextField(blank=True, help_text="Aroma observations")
    color_notes = models.TextField(blank=True, help_text="Color/appearance notes")
    
    class Meta:
        ordering = ['-note_date']
    
    def __str__(self):
        return f"{self.brew_session.batch_name} - {self.title}"

class FermentationPhoto(TimeStampedModel):
    """
    Photos during fermentation process
    """
    brew_session = models.ForeignKey(BrewSession, on_delete=models.CASCADE)
    fermentation_note = models.ForeignKey(FermentationNote, on_delete=models.CASCADE, null=True, blank=True)
    photo = models.ImageField(upload_to='fermentation_photos/')
    caption = models.CharField(max_length=200, blank=True)
    photo_date = models.DateTimeField(default=timezone.now)
    
    class Meta:
        ordering = ['-photo_date']
    
    def __str__(self):
        return f"{self.brew_session.batch_name} - Photo {self.photo_date.strftime('%Y-%m-%d')}"

class FermentationAlert(TimeStampedModel):
    """
    Alerts and notifications for fermentation events
    """
    ALERT_TYPES = [
        ('temperature', 'Temperature Alert'),
        ('gravity', 'Gravity Reading Due'),
        ('fermentation_complete', 'Fermentation Complete'),
        ('secondary', 'Secondary Fermentation'),
        ('dry_hop', 'Dry Hop Addition'),
        ('packaging', 'Ready for Packaging'),
        ('custom', 'Custom Reminder'),
    ]
    
    brew_session = models.ForeignKey(BrewSession, on_delete=models.CASCADE)
    alert_type = models.CharField(max_length=30, choices=ALERT_TYPES)
    title = models.CharField(max_length=200)
    message = models.TextField()
    alert_date = models.DateTimeField()
    is_sent = models.BooleanField(default=False)
    is_dismissed = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['alert_date']
    
    def __str__(self):
        return f"{self.brew_session.batch_name} - {self.title}"
    
    @property
    def is_due(self):
        """Check if alert is due"""
        return timezone.now() >= self.alert_date and not self.is_dismissed