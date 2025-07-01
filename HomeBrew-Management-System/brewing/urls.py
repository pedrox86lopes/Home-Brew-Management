from django.urls import path
from . import views

urlpatterns = [
    # Brewing Lab
    path('', views.brewing_lab, name='brewing_lab'),
    path('sessions/', views.brew_session_list, name='brew_session_list'),
    path('start/<int:recipe_id>/', views.start_brew_session, name='start_brew_session'),
    path('session/<int:pk>/', views.brew_session_detail, name='brew_session_detail'),
    path('session/<int:pk>/update/', views.update_brew_session, name='update_brew_session'),
    path('session/<int:session_id>/temperature/', views.add_temperature_reading, name='add_temperature_reading'),
    path('session/<int:session_id>/gravity/', views.add_gravity_reading, name='add_gravity_reading'),
    path('session/<int:session_id>/timer/', views.start_timer, name='start_timer'),
    path('session/<int:session_id>/fermentation/start/', views.start_fermentation, name='start_fermentation'),
    path('timer/<int:timer_id>/stop/', views.stop_timer, name='stop_timer'),
    path('step/<int:step_id>/complete/', views.complete_brew_step, name='complete_brew_step'),
    path('calculator/', views.brewing_calculator, name='brewing_calculator'),
    
    # Fermentation Lab
    path('fermentation/', views.fermentation_lab, name='fermentation_lab'),
    path('fermentation/<int:pk>/', views.fermentation_detail, name='fermentation_detail'),
    path('fermentation/<int:session_id>/note/', views.add_fermentation_note, name='add_fermentation_note'),
    path('fermentation/<int:session_id>/complete/', views.complete_fermentation, name='complete_fermentation'),
    path('fermentation/<int:session_id>/alert/', views.create_custom_alert, name='create_custom_alert'),
    path('alert/<int:alert_id>/dismiss/', views.dismiss_alert, name='dismiss_alert'),
    
    # API Endpoints
    path('api/session/<int:session_id>/timers/', views.timer_status_api, name='timer_status_api'),
    path('api/fermentation/<int:session_id>/chart-data/', views.fermentation_chart_data, name='fermentation_chart_data'),
]