from django.contrib import admin
from .models import UserProfile, BeerStyle

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'preferred_batch_size', 'brewing_efficiency', 'created_at']
    list_filter = ['brewing_efficiency', 'created_at']
    search_fields = ['user__username', 'user__email']

@admin.register(BeerStyle)
class BeerStyleAdmin(admin.ModelAdmin):
    list_display = ['style_code', 'name', 'og_min', 'og_max', 'ibu_min', 'ibu_max']
    list_filter = ['og_min', 'ibu_min']
    search_fields = ['name', 'style_code']
    ordering = ['style_code']