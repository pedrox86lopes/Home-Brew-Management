from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count, Avg
from .models import UserProfile
from recipes.models import Recipe
from brewing.models import BrewSession

def home(request):
    """Home/Dashboard view"""
    context = {}
    
    if request.user.is_authenticated:
        # Get user stats
        user_recipes = Recipe.objects.filter(created_by=request.user)
        recent_recipes = user_recipes.order_by('-created_at')[:5]
        
        active_brews = BrewSession.objects.filter(
            brewer=request.user, 
            status='active'
        )
        
        context.update({
            'recent_recipes': recent_recipes,
            'total_recipes': user_recipes.count(),
            'active_brews': active_brews,
            'active_brews_count': active_brews.count(),
        })
    
    return render(request, 'core/home.html', context)

def signup(request):
    """User registration view"""
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Create user profile
            UserProfile.objects.create(user=user)
            login(request, user)
            messages.success(request, 'Account created successfully!')
            return redirect('home')
    else:
        form = UserCreationForm()
    
    return render(request, 'registration/signup.html', {'form': form})

@login_required
def profile(request):
    """User profile view"""
    profile, created = UserProfile.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        profile.preferred_batch_size = float(request.POST.get('preferred_batch_size', 20.0))
        profile.brewing_efficiency = float(request.POST.get('brewing_efficiency', 75.0))
        profile.equipment_notes = request.POST.get('equipment_notes', '')
        profile.save()
        messages.success(request, 'Profile updated successfully!')
        return redirect('profile')
    
    return render(request, 'core/profile.html', {'profile': profile})

# core/urls.py

from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('signup/', views.signup, name='signup'),
    path('profile/', views.profile, name='profile'),
]