# recipes/urls.py

from django.urls import path
from . import views

urlpatterns = [
    path('', views.recipe_list, name='recipe_list'),
    path('create/', views.recipe_create, name='recipe_create'),
    path('<int:pk>/', views.recipe_detail, name='recipe_detail'),
    path('<int:pk>/edit/', views.recipe_edit, name='recipe_edit'),
    path('<int:pk>/delete/', views.recipe_delete, name='recipe_delete'),
    path('<int:pk>/clone/', views.recipe_clone, name='recipe_clone'),
    path('<int:pk>/scale/', views.recipe_scale, name='recipe_scale'),
    path('generator/', views.recipe_generator, name='recipe_generator'),
    path('ai-generator/', views.ai_recipe_generator_django, name='ai_recipe_generator_django'),
    path('ai-save/', views.ai_save_recipe, name='ai_save_recipe'),
]