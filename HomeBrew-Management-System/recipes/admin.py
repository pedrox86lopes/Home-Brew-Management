from django.contrib import admin
from .models import Recipe, Grain, Hop, Yeast, GrainAddition, HopAddition, YeastAddition

class GrainAdditionInline(admin.TabularInline):
    model = GrainAddition
    extra = 1

class HopAdditionInline(admin.TabularInline):
    model = HopAddition
    extra = 1

class YeastAdditionInline(admin.TabularInline):
    model = YeastAddition
    extra = 1

@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = ['name', 'style', 'created_by', 'batch_size', 'calculated_og', 'calculated_ibu', 'created_at']
    list_filter = ['style', 'created_by', 'is_public', 'created_at']
    search_fields = ['name', 'description']
    inlines = [GrainAdditionInline, HopAdditionInline, YeastAdditionInline]
    readonly_fields = ['calculated_og', 'calculated_fg', 'calculated_ibu', 'calculated_srm', 'calculated_abv']

@admin.register(Grain)
class GrainAdmin(admin.ModelAdmin):
    list_display = ['name', 'grain_type', 'color', 'extract_potential']
    list_filter = ['grain_type', 'color']
    search_fields = ['name']
    ordering = ['grain_type', 'name']

@admin.register(Hop)
class HopAdmin(admin.ModelAdmin):
    list_display = ['name', 'hop_type', 'alpha_acid']
    list_filter = ['hop_type', 'alpha_acid']