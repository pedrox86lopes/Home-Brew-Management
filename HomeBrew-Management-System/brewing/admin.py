from django.contrib import admin
from .models import BrewSession, BrewStepLog, TemperatureReading, GravityReading, BrewTimer

@admin.register(BrewSession)
class BrewSessionAdmin(admin.ModelAdmin):
    list_display = ['batch_name', 'recipe', 'brewer', 'status', 'current_stage', 'brew_date']
    list_filter = ['status', 'current_stage', 'brewer', 'brew_date']
    search_fields = ['batch_name', 'recipe__name']
    readonly_fields = ['actual_abv']

@admin.register(BrewStepLog)
class BrewStepLogAdmin(admin.ModelAdmin):
    list_display = ['brew_session', 'step_name', 'step_type', 'start_time', 'is_completed']
    list_filter = ['step_type', 'is_completed', 'start_time']
    search_fields = ['step_name', 'brew_session__batch_name']

@admin.register(TemperatureReading)
class TemperatureReadingAdmin(admin.ModelAdmin):
    list_display = ['brew_session', 'temperature', 'reading_type', 'timestamp']
    list_filter = ['reading_type', 'timestamp']
    search_fields = ['brew_session__batch_name']

@admin.register(GravityReading)
class GravityReadingAdmin(admin.ModelAdmin):
    list_display = ['brew_session', 'gravity', 'reading_type', 'timestamp']
    list_filter = ['reading_type', 'timestamp']
    search_fields = ['brew_session__batch_name']