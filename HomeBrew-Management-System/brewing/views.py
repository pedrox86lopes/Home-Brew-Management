from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Q, Avg, Count
from datetime import timedelta
from .models import (BrewSession, BrewStepLog, TemperatureReading, GravityReading, 
                     BrewTimer, FermentationNote, FermentationPhoto, FermentationAlert)
from recipes.models import Recipe
from core.models import BrewingCalculator
import json

@login_required
def brewing_lab(request):
    """Main brewing lab dashboard"""
    # Get active brew sessions
    active_sessions = BrewSession.objects.filter(
        brewer=request.user,
        status__in=['active', 'fermenting', 'conditioning']
    ).order_by('-brew_date')
    
    # Get recent completed sessions
    recent_sessions = BrewSession.objects.filter(
        brewer=request.user,
        status='completed'
    ).order_by('-brew_date')[:5]
    
    # Get available recipes for new brews
    available_recipes = Recipe.objects.filter(created_by=request.user)[:10]
    
    # Get pending alerts - handle case where model doesn't exist yet
    try:
        pending_alerts = FermentationAlert.objects.filter(
            brew_session__brewer=request.user,
            alert_date__lte=timezone.now(),
            is_dismissed=False
        )[:5]
    except:
        pending_alerts = []
    
    context = {
        'active_sessions': active_sessions,
        'recent_sessions': recent_sessions,
        'available_recipes': available_recipes,
        'pending_alerts': pending_alerts,
    }
    
    return render(request, 'brewing/brewing_lab.html', context)

@login_required
def start_brew_session(request, recipe_id):
    """Start a new brewing session"""
    recipe = get_object_or_404(Recipe, id=recipe_id, created_by=request.user)
    
    if request.method == 'POST':
        batch_name = request.POST.get('batch_name', f"{recipe.name} - {timezone.now().strftime('%Y-%m-%d')}")
        actual_batch_size = float(request.POST.get('actual_batch_size', recipe.batch_size))
        
        # Create brew session
        brew_session = BrewSession.objects.create(
            recipe=recipe,
            brewer=request.user,
            batch_name=batch_name,
            actual_batch_size=actual_batch_size,
            status='active',
            current_stage='preparation'
        )
        
        # Create initial brewing steps
        create_initial_brew_steps(brew_session)
        
        # Create initial fermentation alerts
        create_fermentation_alerts(brew_session)
        
        messages.success(request, f'Started brewing session: {batch_name}')
        return redirect('brew_session_detail', pk=brew_session.pk)
    
    context = {
        'recipe': recipe,
        'suggested_name': f"{recipe.name} - Batch {timezone.now().strftime('%Y%m%d')}",
    }
    
    return render(request, 'brewing/start_brew_session.html', context)

def create_initial_brew_steps(brew_session):
    """Create initial brewing steps for BIAB process"""
    recipe = brew_session.recipe
    
    # Calculate water requirements
    grain_weight = recipe.total_grain_weight()
    total_water = brew_session.actual_batch_size + BrewingCalculator.calculate_grain_absorption(grain_weight)
    strike_temp = BrewingCalculator.calculate_strike_water_temp(20, 67, total_water/grain_weight)
    
    steps = [
        {
            'name': 'Heat Strike Water',
            'type': 'temperature',
            'target_temp': strike_temp,
            'duration': 30,
            'notes': f'Heat {total_water:.1f}L water to {strike_temp:.1f}°C'
        },
        {
            'name': 'Mash In',
            'type': 'mash',
            'target_temp': 67,
            'duration': 60,
            'notes': 'Add grain bag and maintain temperature at 67°C for 60 minutes'
        },
        {
            'name': 'Mash Out',
            'type': 'mash',
            'target_temp': 76,
            'duration': 10,
            'notes': 'Raise temperature to 76°C for mash out'
        },
        {
            'name': 'Remove Grain Bag',
            'type': 'transfer',
            'duration': 15,
            'notes': 'Lift grain bag and allow to drain'
        },
        {
            'name': 'Bring to Boil',
            'type': 'temperature',
            'target_temp': 100,
            'duration': 15,
            'notes': 'Heat wort to rolling boil'
        },
    ]
    
    # Add hop additions in reverse order (longest boil time first)
    for hop_addition in recipe.hopaddition_set.all().order_by('-boil_time'):
        if hop_addition.use == 'boil':
            steps.append({
                'name': f'Add {hop_addition.hop.name}',
                'type': 'boil',
                'duration': hop_addition.boil_time,
                'notes': f'Add {hop_addition.weight*1000:.1f}g {hop_addition.hop.name} hops at {hop_addition.boil_time} minutes'
            })
    
    # Add final steps
    steps.extend([
        {
            'name': 'End Boil',
            'type': 'boil',
            'duration': 0,
            'notes': 'Turn off heat, add any flameout hops'
        },
        {
            'name': 'Cool Wort',
            'type': 'temperature',
            'target_temp': 20,
            'duration': 30,
            'notes': 'Cool wort to pitching temperature (18-22°C)'
        },
        {
            'name': 'Transfer to Fermenter',
            'type': 'transfer',
            'duration': 15,
            'notes': 'Transfer cooled wort to fermenter, leaving trub behind'
        },
        {
            'name': 'Pitch Yeast',
            'type': 'note',
            'duration': 5,
            'notes': 'Add yeast and aerate if needed. Record OG.'
        }
    ])
    
    # Create step log entries
    for i, step in enumerate(steps):
        BrewStepLog.objects.create(
            brew_session=brew_session,
            step_name=step['name'],
            step_type=step['type'],
            target_temperature=step.get('target_temp'),
            notes=step['notes']
        )

def create_fermentation_alerts(brew_session):
    """Create initial fermentation alerts"""
    base_date = timezone.now()
    
    # Primary fermentation check (3 days)
    FermentationAlert.objects.create(
        brew_session=brew_session,
        alert_type='gravity',
        title='Check Fermentation Progress',
        message='Take a gravity reading to check fermentation progress',
        alert_date=base_date + timedelta(days=3)
    )
    
    # Estimated fermentation completion (10-14 days for ales, 14-21 for lagers)
    days = 14 if 'ale' in brew_session.recipe.style.name.lower() else 21
    FermentationAlert.objects.create(
        brew_session=brew_session,
        alert_type='fermentation_complete',
        title='Fermentation Likely Complete',
        message='Check final gravity and consider transferring to secondary or packaging',
        alert_date=base_date + timedelta(days=days)
    )

@login_required
def brew_session_detail(request, pk):
    """Detailed view of brewing session"""
    session = get_object_or_404(BrewSession, pk=pk, brewer=request.user)
    
    # Get brewing steps
    steps = BrewStepLog.objects.filter(brew_session=session)
    current_step = steps.filter(is_completed=False).first()
    
    # Get active timers
    active_timers = BrewTimer.objects.filter(brew_session=session, is_active=True)
    
    # Get recent readings
    temp_readings = TemperatureReading.objects.filter(brew_session=session)[:10]
    gravity_readings = GravityReading.objects.filter(brew_session=session)[:10]
    
    context = {
        'session': session,
        'steps': steps,
        'current_step': current_step,
        'active_timers': active_timers,
        'temp_readings': temp_readings,
        'gravity_readings': gravity_readings,
    }
    
    return render(request, 'brewing/brew_session_detail.html', context)

@login_required
def fermentation_lab(request):
    """Fermentation lab dashboard"""
    # Get fermenting sessions
    fermenting_sessions = BrewSession.objects.filter(
        brewer=request.user,
        status='fermenting'
    ).order_by('-fermentation_start')
    
    # Get sessions ready for packaging
    ready_sessions = BrewSession.objects.filter(
        brewer=request.user,
        status='conditioning'
    ).order_by('-fermentation_end')
    
    # Get recent fermentation notes
    recent_notes = FermentationNote.objects.filter(
        brew_session__brewer=request.user
    ).order_by('-note_date')[:10]
    
    # Get pending alerts - handle case where model doesn't exist yet
    try:
        pending_alerts = FermentationAlert.objects.filter(
            brew_session__brewer=request.user,
            alert_date__lte=timezone.now(),
            is_dismissed=False
        ).order_by('alert_date')
    except:
        pending_alerts = []
    
    context = {
        'fermenting_sessions': fermenting_sessions,
        'ready_sessions': ready_sessions,
        'recent_notes': recent_notes,
        'pending_alerts': pending_alerts,
    }
    
    return render(request, 'brewing/fermentation_lab.html', context)

@login_required
def fermentation_detail(request, pk):
    """Detailed fermentation tracking"""
    session = get_object_or_404(BrewSession, pk=pk, brewer=request.user)
    
    # Get fermentation data
    notes = FermentationNote.objects.filter(brew_session=session).order_by('-note_date')
    photos = FermentationPhoto.objects.filter(brew_session=session).order_by('-photo_date')
    temp_readings = TemperatureReading.objects.filter(
        brew_session=session, 
        reading_type='fermentation'
    ).order_by('-timestamp')[:20]
    gravity_readings = GravityReading.objects.filter(brew_session=session).order_by('-timestamp')
    
    # Calculate fermentation stats
    fermentation_progress = session.get_fermentation_progress()
    estimated_completion = session.estimated_fermentation_end
    
    context = {
        'session': session,
        'notes': notes,
        'photos': photos,
        'temp_readings': temp_readings,
        'gravity_readings': gravity_readings,
        'fermentation_progress': fermentation_progress,
        'estimated_completion': estimated_completion,
    }
    
    return render(request, 'brewing/fermentation_detail.html', context)

@login_required
def add_fermentation_note(request, session_id):
    """Add fermentation note"""
    session = get_object_or_404(BrewSession, pk=session_id, brewer=request.user)
    
    if request.method == 'POST':
        title = request.POST.get('title')
        content = request.POST.get('content')
        krausen_activity = request.POST.get('krausen_activity')
        aroma_notes = request.POST.get('aroma_notes', '')
        color_notes = request.POST.get('color_notes', '')
        is_public = request.POST.get('is_public') == 'on'
        
        note = FermentationNote.objects.create(
            brew_session=session,
            title=title,
            content=content,
            krausen_activity=krausen_activity,
            aroma_notes=aroma_notes,
            color_notes=color_notes,
            is_public=is_public
        )
        
        # Handle photo uploads
        if 'photos' in request.FILES:
            for photo in request.FILES.getlist('photos'):
                FermentationPhoto.objects.create(
                    brew_session=session,
                    fermentation_note=note,
                    photo=photo,
                    caption=f"Photo from {note.title}"
                )
        
        messages.success(request, 'Fermentation note added successfully!')
        return redirect('fermentation_detail', pk=session.pk)
    
    return render(request, 'brewing/add_fermentation_note.html', {'session': session})

@login_required
def add_temperature_reading(request, session_id):
    """Add temperature reading"""
    session = get_object_or_404(BrewSession, pk=session_id, brewer=request.user)
    
    if request.method == 'POST':
        temperature = float(request.POST.get('temperature'))
        reading_type = request.POST.get('reading_type', 'fermentation')
        notes = request.POST.get('notes', '')
        
        TemperatureReading.objects.create(
            brew_session=session,
            temperature=temperature,
            reading_type=reading_type,
            notes=notes
        )
        
        messages.success(request, f'Added temperature reading: {temperature}°C')
        
        if request.headers.get('HX-Request'):
            readings = TemperatureReading.objects.filter(brew_session=session)[:5]
            return render(request, 'brewing/partials/temp_readings.html', {'readings': readings})
        
        return redirect('brew_session_detail', pk=session.pk)
    
    return JsonResponse({'error': 'Invalid request'}, status=400)

@login_required
def add_gravity_reading(request, session_id):
    """Add gravity reading"""
    session = get_object_or_404(BrewSession, pk=session_id, brewer=request.user)
    
    if request.method == 'POST':
        gravity = float(request.POST.get('gravity'))
        reading_type = request.POST.get('reading_type', 'progress')
        temperature = request.POST.get('temperature')
        notes = request.POST.get('notes', '')
        
        reading = GravityReading.objects.create(
            brew_session=session,
            gravity=gravity,
            reading_type=reading_type,
            temperature=float(temperature) if temperature else None,
            notes=notes
        )
        
        # Update session if this is OG or FG
        if reading_type == 'original':
            session.actual_og = gravity
            session.save()
        elif reading_type == 'final':
            session.actual_fg = gravity
            if session.actual_og:
                session.actual_abv = BrewingCalculator.calculate_abv(session.actual_og, gravity)
            session.save()
        
        messages.success(request, f'Added gravity reading: SG {gravity}')
        
        if request.headers.get('HX-Request'):
            readings = GravityReading.objects.filter(brew_session=session)[:5]
            return render(request, 'brewing/partials/gravity_readings.html', {'readings': readings})
        
        return redirect('fermentation_detail', pk=session.pk)
    
    return JsonResponse({'error': 'Invalid request'}, status=400)

@login_required
def start_fermentation(request, session_id):
    """Move brew session to fermentation stage"""
    session = get_object_or_404(BrewSession, pk=session_id, brewer=request.user)
    
    if request.method == 'POST':
        session.status = 'fermenting'
        session.current_stage = 'fermentation'
        session.fermentation_start = timezone.now()
        session.save()
        
        messages.success(request, f'Started fermentation for {session.batch_name}')
        return redirect('fermentation_detail', pk=session.pk)
    
    return redirect('brew_session_detail', pk=session.pk)

@login_required
def complete_fermentation(request, session_id):
    """Complete fermentation and move to conditioning"""
    session = get_object_or_404(BrewSession, pk=session_id, brewer=request.user)
    
    if request.method == 'POST':
        session.status = 'conditioning'
        session.current_stage = 'conditioning'
        session.fermentation_end = timezone.now()
        session.save()
        
        # Create packaging alert
        FermentationAlert.objects.create(
            brew_session=session,
            alert_type='packaging',
            title='Ready for Packaging',
            message=f'{session.batch_name} is ready for bottling or kegging',
            alert_date=timezone.now() + timedelta(days=3)
        )
        
        messages.success(request, f'Fermentation completed for {session.batch_name}')
        return redirect('fermentation_detail', pk=session.pk)
    
    return redirect('fermentation_detail', pk=session.pk)

@login_required
def start_timer(request, session_id):
    """Start a brewing timer"""
    session = get_object_or_404(BrewSession, pk=session_id, brewer=request.user)
    
    if request.method == 'POST':
        name = request.POST.get('name')
        duration = int(request.POST.get('duration'))
        
        timer = BrewTimer.objects.create(
            brew_session=session,
            name=name,
            duration_minutes=duration
        )
        
        messages.success(request, f'Started timer: {name} ({duration} minutes)')
        
        if request.headers.get('HX-Request'):
            timers = BrewTimer.objects.filter(brew_session=session, is_active=True)
            return render(request, 'brewing/partials/active_timers.html', {'timers': timers})
        
        return redirect('brew_session_detail', pk=session.pk)
    
    return JsonResponse({'error': 'Invalid request'}, status=400)

@login_required
def stop_timer(request, timer_id):
    """Stop a brewing timer"""
    timer = get_object_or_404(BrewTimer, pk=timer_id, brew_session__brewer=request.user)
    timer.stop_timer()
    
    messages.success(request, f'Stopped timer: {timer.name}')
    
    if request.headers.get('HX-Request'):
        timers = BrewTimer.objects.filter(brew_session=timer.brew_session, is_active=True)
        return render(request, 'brewing/partials/active_timers.html', {'timers': timers})
    
    return redirect('brew_session_detail', pk=timer.brew_session.pk)

@login_required
def complete_brew_step(request, step_id):
    """Mark a brewing step as completed"""
    step = get_object_or_404(BrewStepLog, pk=step_id, brew_session__brewer=request.user)
    
    if request.method == 'POST':
        actual_temp = request.POST.get('actual_temperature')
        notes = request.POST.get('notes', step.notes)
        
        step.actual_temperature = float(actual_temp) if actual_temp else None
        step.notes = notes
        step.complete_step()
        
        messages.success(request, f'Completed step: {step.step_name}')
        
        # Update session stage if needed
        update_session_stage(step.brew_session)
        
        return redirect('brew_session_detail', pk=step.brew_session.pk)
    
    return render(request, 'brewing/complete_step.html', {'step': step})

def update_session_stage(session):
    """Update brewing session stage based on completed steps"""
    completed_steps = session.brewsteplog_set.filter(is_completed=True).count()
    total_steps = session.brewsteplog_set.count()
    
    # Check if all brewing steps are complete
    if completed_steps >= total_steps:
        session.current_stage = 'cooling'
        # Don't auto-start fermentation - let user decide when to pitch yeast
    elif any('Boil' in step.step_name for step in session.brewsteplog_set.filter(is_completed=True)):
        session.current_stage = 'boiling'
    elif any('Mash' in step.step_name for step in session.brewsteplog_set.filter(is_completed=True)):
        session.current_stage = 'mashing'
    
    session.save()

@login_required
def update_brew_session(request, pk):
    """Update brewing session details"""
    session = get_object_or_404(BrewSession, pk=pk, brewer=request.user)
    
    if request.method == 'POST':
        session.batch_name = request.POST.get('batch_name', session.batch_name)
        session.status = request.POST.get('status', session.status)
        session.current_stage = request.POST.get('current_stage', session.current_stage)
        session.notes = request.POST.get('notes', session.notes)
        
        # Handle date fields
        if request.POST.get('fermentation_start'):
            session.fermentation_start = timezone.datetime.fromisoformat(
                request.POST.get('fermentation_start')
            )
        
        if request.POST.get('fermentation_end'):
            session.fermentation_end = timezone.datetime.fromisoformat(
                request.POST.get('fermentation_end')
            )
        
        session.save()
        messages.success(request, 'Brewing session updated successfully!')
        
        return redirect('brew_session_detail', pk=session.pk)
    
    return render(request, 'brewing/update_session.html', {'session': session})

@login_required
def brew_session_list(request):
    """List all brewing sessions"""
    sessions = BrewSession.objects.filter(brewer=request.user)
    
    # Filter by status
    status_filter = request.GET.get('status')
    if status_filter:
        sessions = sessions.filter(status=status_filter)
    
    # Search
    search_query = request.GET.get('search')
    if search_query:
        sessions = sessions.filter(
            Q(batch_name__icontains=search_query) |
            Q(recipe__name__icontains=search_query)
        )
    
    sessions = sessions.order_by('-brew_date')
    
    context = {
        'sessions': sessions,
        'status_filter': status_filter,
        'search_query': search_query,
    }
    
    return render(request, 'brewing/session_list.html', context)

@login_required
def brewing_calculator(request):
    """Brewing calculator utilities"""
    if request.method == 'POST':
        calc_type = request.POST.get('calc_type')
        result = None
        
        if calc_type == 'strike_water':
            grain_temp = float(request.POST.get('grain_temp', 20))
            mash_temp = float(request.POST.get('mash_temp', 67))
            water_ratio = float(request.POST.get('water_ratio', 3))
            
            result = BrewingCalculator.calculate_strike_water_temp(
                grain_temp, mash_temp, water_ratio
            )
            
        elif calc_type == 'abv':
            og = float(request.POST.get('og'))
            fg = float(request.POST.get('fg'))
            result = BrewingCalculator.calculate_abv(og, fg)
            
        elif calc_type == 'attenuation':
            og = float(request.POST.get('og'))
            fg = float(request.POST.get('fg'))
            result = BrewingCalculator.calculate_attenuation(og, fg)
        
        if request.headers.get('HX-Request'):
            return JsonResponse({'result': result})
        
        context = {'result': result, 'calc_type': calc_type}
        return render(request, 'brewing/calculator.html', context)
    
    return render(request, 'brewing/calculator.html')

@login_required
def dismiss_alert(request, alert_id):
    """Dismiss a fermentation alert"""
    alert = get_object_or_404(FermentationAlert, pk=alert_id, brew_session__brewer=request.user)
    alert.is_dismissed = True
    alert.save()
    
    if request.headers.get('HX-Request'):
        return JsonResponse({'status': 'dismissed'})
    
    return redirect('fermentation_lab')

@login_required
def create_custom_alert(request, session_id):
    """Create custom fermentation alert"""
    session = get_object_or_404(BrewSession, pk=session_id, brewer=request.user)
    
    if request.method == 'POST':
        title = request.POST.get('title')
        message = request.POST.get('message')
        alert_date = timezone.datetime.fromisoformat(request.POST.get('alert_date'))
        
        FermentationAlert.objects.create(
            brew_session=session,
            alert_type='custom',
            title=title,
            message=message,
            alert_date=alert_date
        )
        
        messages.success(request, 'Custom alert created successfully!')
        return redirect('fermentation_detail', pk=session.pk)
    
    return render(request, 'brewing/create_alert.html', {'session': session})

# API endpoint for timer status
@login_required
def timer_status_api(request, session_id):
    """API endpoint for timer status updates"""
    session = get_object_or_404(BrewSession, pk=session_id, brewer=request.user)
    timers = BrewTimer.objects.filter(brew_session=session, is_active=True)
    
    timer_data = []
    for timer in timers:
        timer_data.append({
            'id': timer.id,
            'name': timer.name,
            'time_remaining': timer.time_remaining,
            'is_finished': timer.is_finished,
            'duration_minutes': timer.duration_minutes
        })
    
    return JsonResponse({'timers': timer_data})

@login_required
def fermentation_chart_data(request, session_id):
    """API endpoint for fermentation chart data"""
    session = get_object_or_404(BrewSession, pk=session_id, brewer=request.user)
    
    # Get temperature data
    temp_readings = TemperatureReading.objects.filter(
        brew_session=session,
        reading_type='fermentation'
    ).order_by('timestamp')
    
    # Get gravity data
    gravity_readings = GravityReading.objects.filter(
        brew_session=session
    ).order_by('timestamp')
    
    temp_data = [
        {
            'timestamp': reading.timestamp.isoformat(),
            'temperature': float(reading.temperature)
        }
        for reading in temp_readings
    ]
    
    gravity_data = [
        {
            'timestamp': reading.timestamp.isoformat(),
            'gravity': float(reading.gravity),
            'type': reading.reading_type
        }
        for reading in gravity_readings
    ]
    
    return JsonResponse({
        'temperature_data': temp_data,
        'gravity_data': gravity_data
    })
    