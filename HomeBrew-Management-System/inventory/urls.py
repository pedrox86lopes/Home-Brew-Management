from django.urls import path
from . import views

urlpatterns = [
    path('', views.inventory_list, name='inventory_list'),
    path('<int:pk>/', views.inventory_detail, name='inventory_detail'),
    path('add/', views.ingredient_add, name='ingredient_add'),
    path('<int:pk>/update-stock/', views.inventory_update_stock, name='inventory_update_stock'),
    path('shopping-list/', views.shopping_list_view, name='shopping_list'),
    path('shopping-list/add/', views.add_to_shopping_list, name='add_to_shopping_list'),
    path('shopping-list/from-recipe/<int:recipe_id>/', views.generate_shopping_list_from_recipe, name='shopping_list_from_recipe'),
]