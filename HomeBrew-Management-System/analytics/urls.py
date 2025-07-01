from django.urls import path
from . import views

urlpatterns = [
    path('', views.analytics_dashboard, name='analytics_dashboard'),
    path('performance/', views.brewing_performance, name='brewing_performance'),
    path('costs/', views.cost_analysis, name='cost_analysis'),
    path('fermentation/', views.fermentation_tracking, name='fermentation_tracking'),
    path('inventory/', views.inventory_analytics, name='inventory_analytics'),
]