from django.contrib import admin
from .models import InventoryItem, InventoryTransaction, Supplier, ShoppingList, ShoppingListItem

@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ['name', 'website', 'contact_email', 'is_active']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'contact_email']

@admin.register(InventoryItem)
class InventoryItemAdmin(admin.ModelAdmin):
    list_display = ['ingredient_name', 'ingredient_type', 'current_stock', 'unit', 'cost_per_unit', 'user']
    list_filter = ['ingredient_type', 'unit', 'user']
    search_fields = ['ingredient_name']
    readonly_fields = ['ingredient_name']

@admin.register(InventoryTransaction)
class InventoryTransactionAdmin(admin.ModelAdmin):
    list_display = ['inventory_item', 'transaction_type', 'quantity', 'unit', 'created_at']
    list_filter = ['transaction_type', 'created_at']
    search_fields = ['inventory_item__ingredient_name']

@admin.register(ShoppingList)
class ShoppingListAdmin(admin.ModelAdmin):
    list_display = ['name', 'user', 'is_active', 'created_at']
    list_filter = ['is_active', 'user', 'created_at']
    search_fields = ['name']