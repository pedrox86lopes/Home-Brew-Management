from django.contrib import admin
from .models import BrewingStats

@admin.register(BrewingStats)
class BrewingStatsAdmin(admin.ModelAdmin):
    list_display = ['user', 'total_brews', 'avg_efficiency', 'avg_abv', 'last_updated']
    list_filter = ['last_updated']
    search_fields = ['user__username']
    readonly_fields = ['last_updated']
