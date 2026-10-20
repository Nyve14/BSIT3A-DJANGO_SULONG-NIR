from collections import defaultdict

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import models
from django.db.models import Q, Count
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import TransitAgency, TransitAlert, TransitRoute, TransitSchedule, TransitStop


def _can_manage_transit(user):
    return user.is_staff or user.is_superuser


def transit_home(request):
    agencies = TransitAgency.objects.filter(is_active=True).prefetch_related(
        'routes__stops'
    ).annotate(
        route_count=models.Count('routes', filter=Q(routes__is_active=True))
    )
    active_alerts = TransitAlert.objects.filter(
        is_active=True,
        starts_at__lte=timezone.now(),
    ).filter(
        models.Q(ends_at__isnull=True) | models.Q(ends_at__gte=timezone.now())
    ).select_related('route', 'agency')[:5]

    return render(request, 'transit/home.html', {
        'agencies': agencies,
        'active_alerts': active_alerts,
        'can_manage': _can_manage_transit(request.user),
    })


def transit_map(request):
    """Return GeoJSON of routes and stops for map display."""
    routes = TransitRoute.objects.filter(is_active=True).select_related('agency')
    features = []
    for route in routes:
        stops = route.stops.filter(is_active=True).order_by('sequence')
        coordinates = []
        for stop in stops:
            coordinates.append([float(stop.longitude), float(stop.latitude)])
        if coordinates:
            features.append({
                'type': 'Feature',
                'geometry': {
                    'type': 'LineString',
                    'coordinates': coordinates,
                },
                'properties': {
                    'route_id': route.id,
                    'short_name': route.short_name,
                    'long_name': route.long_name,
                    'vehicle_type': route.vehicle_type,
                    'color': route.color,
                    'agency': route.agency.short_name,
                },
            })
        # Add stops as points
        for stop in stops:
            features.append({
                'type': 'Feature',
                'geometry': {
                    'type': 'Point',
                    'coordinates': [float(stop.longitude), float(stop.latitude)],
                },
                'properties': {
                    'stop_id': stop.id,
                    'name': stop.name,
                    'route': route.short_name,
                    'stop_type': stop.stop_type,
                    'sequence': stop.sequence,
                    'landmarks': stop.landmarks,
                },
            })
    return JsonResponse({
        'type': 'FeatureCollection',
        'features': features,
    })


def route_list(request):
    routes = TransitRoute.objects.select_related('agency').filter(is_active=True).order_by('short_name')

    q = request.GET.get('q', '').strip()
    vehicle_type = request.GET.get('vehicle_type')
    agency = request.GET.get('agency')

    if q:
        routes = routes.filter(
            Q(short_name__icontains=q) | Q(long_name__icontains=q) | Q(description__icontains=q)
        )
    if vehicle_type:
        routes = routes.filter(vehicle_type=vehicle_type)
    if agency:
        routes = routes.filter(agency_id=agency)

    # Annotate each route with the count of active stops
    routes = routes.annotate(
        active_stops_count=Count('stops', filter=Q(stops__is_active=True))
    )

    paginator = Paginator(routes, 10)
    page = paginator.get_page(request.GET.get('page', 1))

    agencies = TransitAgency.objects.filter(is_active=True)

    return render(request, 'transit/route_list.html', {
        'routes': page,
        'agencies': agencies,
        'q': q,
        'selected_vehicle_type': vehicle_type,
        'selected_agency': agency,
        'vehicle_types': TransitRoute.VehicleType.choices,
    })


def route_detail(request, pk):
    route = get_object_or_404(
        TransitRoute.objects.select_related('agency').prefetch_related('stops', 'schedules__origin_stop', 'schedules__destination_stop', 'alerts'),
        pk=pk,
        is_active=True,
    )
    stops = route.stops.filter(is_active=True).order_by('sequence')
    schedules = route.schedules.filter(is_active=True).select_related('origin_stop', 'destination_stop').order_by('day_of_week', 'departure_time')
    alerts = route.alerts.filter(is_active=True).order_by('-starts_at')

    # Group schedules by day
    from collections import defaultdict
    schedules_by_day = defaultdict(list)
    for sched in schedules:
        schedules_by_day[sched.day_of_week].append(sched)

    return render(request, 'transit/route_detail.html', {
        'route': route,
        'stops': stops,
        'schedules_by_day': dict(schedules_by_day),
        'alerts': alerts,
        'days_of_week': TransitSchedule.DayOfWeek.choices,
    })


def schedule_list(request):
    """API endpoint for schedules."""
    route_id = request.GET.get('route_id')
    day = request.GET.get('day')

    schedules = TransitSchedule.objects.filter(is_active=True).select_related(
        'route', 'origin_stop', 'destination_stop'
    )
    if route_id:
        schedules = schedules.filter(route_id=route_id)
    if day is not None:
        schedules = schedules.filter(day_of_week=int(day))

    data = []
    for s in schedules.order_by('day_of_week', 'departure_time')[:100]:
        data.append({
            'id': s.id,
            'route': s.route.short_name,
            'day': s.get_day_of_week_display(),
            'departure_time': s.departure_time.strftime('%H:%M'),
            'origin': s.origin_stop.name,
            'destination': s.destination_stop.name,
            'duration': s.estimated_duration_minutes,
            'frequency': s.frequency_minutes,
        })
    return JsonResponse({'schedules': data})


def stops_nearby(request):
    """API endpoint for nearby stops."""
    from django.contrib.gis.geos import Point
    from django.contrib.gis.measure import D
    from django.contrib.gis.db.models.functions import Distance

    lat = request.GET.get('lat')
    lng = request.GET.get('lng')
    radius_km = float(request.GET.get('radius', 2))

    if lat and lng:
        point = Point(float(lng), float(lat), srid=4326)
        stops = TransitStop.objects.filter(
            is_active=True,
            location__distance_lte=(point, D(km=radius_km)),
        ).annotate(distance=Distance('location', point)).select_related('route', 'route__agency').order_by('distance')[:20]
    else:
        stops = TransitStop.objects.filter(is_active=True).select_related('route', 'route__agency')[:20]

    data = []
    for stop in stops:
        data.append({
            'id': stop.id,
            'name': stop.name,
            'lat': float(stop.latitude),
            'lng': float(stop.longitude),
            'route': stop.route.short_name,
            'route_color': stop.route.color,
            'vehicle_type': stop.route.vehicle_type,
            'stop_type': stop.stop_type,
        })
    return JsonResponse({'stops': data})


def alerts_list(request):
    """API endpoint for active alerts."""
    alerts = TransitAlert.objects.filter(
        is_active=True,
        starts_at__lte=timezone.now(),
    ).filter(
        models.Q(ends_at__isnull=True) | models.Q(ends_at__gte=timezone.now())
    ).select_related('route', 'agency').order_by('-severity', '-starts_at')[:50]

    data = []
    for alert in alerts:
        data.append({
            'id': alert.id,
            'title': alert.title,
            'message': alert.message,
            'severity': alert.severity,
            'route': alert.route.short_name if alert.route else None,
            'agency': alert.agency.short_name,
            'starts_at': alert.starts_at.isoformat(),
            'ends_at': alert.ends_at.isoformat() if alert.ends_at else None,
        })
    return JsonResponse({'alerts': data})


@login_required(login_url='login')
def agency_create(request):
    if not _can_manage_transit(request.user):
        messages.error(request, 'Permission denied.')
        return redirect('transit:home')

    if request.method == 'POST':
        agency = TransitAgency.objects.create(
            name=request.POST['name'],
            short_name=request.POST['short_name'],
            description=request.POST.get('description', ''),
            website=request.POST.get('website', ''),
            phone=request.POST.get('phone', ''),
            email=request.POST.get('email', ''),
        )
        messages.success(request, 'Agency created.')
        return redirect('transit:home')
    return render(request, 'transit/agency_form.html')


@login_required(login_url='login')
def route_create(request):
    if not _can_manage_transit(request.user):
        messages.error(request, 'Permission denied.')
        return redirect('transit:route_list')

    if request.method == 'POST':
        route = TransitRoute.objects.create(
            agency_id=request.POST['agency'],
            short_name=request.POST['short_name'],
            long_name=request.POST.get('long_name', ''),
            description=request.POST.get('description', ''),
            vehicle_type=request.POST['vehicle_type'],
            color=request.POST.get('color', '#3B82F6'),
        )
        messages.success(request, 'Route created.')
        return redirect('transit:route_detail', pk=route.pk)

    agencies = TransitAgency.objects.filter(is_active=True)
    return render(request, 'transit/route_form.html', {
        'agencies': agencies,
        'vehicle_types': TransitRoute.VehicleType.choices,
    })


@login_required(login_url='login')
def route_edit(request, pk):
    if not _can_manage_transit(request.user):
        messages.error(request, 'Permission denied.')
        return redirect('transit:route_list')

    route = get_object_or_404(TransitRoute, pk=pk)
    if request.method == 'POST':
        route.short_name = request.POST['short_name']
        route.long_name = request.POST.get('long_name', '')
        route.description = request.POST.get('description', '')
        route.vehicle_type = request.POST['vehicle_type']
        route.color = request.POST.get('color', route.color)
        route.save()
        messages.success(request, 'Route updated.')
        return redirect('transit:route_detail', pk=route.pk)

    agencies = TransitAgency.objects.filter(is_active=True)
    return render(request, 'transit/route_form.html', {
        'route': route,
        'agencies': agencies,
        'vehicle_types': TransitRoute.VehicleType.choices,
    })


@login_required(login_url='login')
@require_POST
def route_delete(request, pk):
    if not _can_manage_transit(request.user):
        messages.error(request, 'Permission denied.')
        return redirect('transit:route_list')

    route = get_object_or_404(TransitRoute, pk=pk)
    route.delete()
    messages.success(request, 'Route deleted.')
    return redirect('transit:route_list')


@login_required(login_url='login')
def stop_create(request, route_pk):
    if not _can_manage_transit(request.user):
        messages.error(request, 'Permission denied.')
        return redirect('transit:route_detail', pk=route_pk)

    route = get_object_or_404(TransitRoute, pk=route_pk)
    if request.method == 'POST':
        last_seq = route.stops.aggregate(models.Max('sequence'))['sequence__max'] or 0
        TransitStop.objects.create(
            route=route,
            name=request.POST['name'],
            latitude=request.POST['latitude'],
            longitude=request.POST['longitude'],
            sequence=int(request.POST.get('sequence', last_seq + 1)),
            stop_type=request.POST.get('stop_type', 'regular'),
            estimated_time_minutes=request.POST.get('estimated_time_minutes') or None,
            landmarks=request.POST.get('landmarks', ''),
        )
        messages.success(request, 'Stop added.')
        return redirect('transit:route_detail', pk=route.pk)

    return render(request, 'transit/stop_form.html', {'route': route})


@login_required(login_url='login')
@require_POST
def stop_delete(request, pk):
    if not _can_manage_transit(request.user):
        messages.error(request, 'Permission denied.')
        return redirect('transit:route_list')

    stop = get_object_or_404(TransitStop, pk=pk)
    route_pk = stop.route_id
    stop.delete()
    messages.success(request, 'Stop deleted.')
    return redirect('transit:route_detail', pk=route_pk)


@login_required(login_url='login')
def schedule_create(request, route_pk):
    if not _can_manage_transit(request.user):
        messages.error(request, 'Permission denied.')
        return redirect('transit:route_detail', pk=route_pk)

    route = get_object_or_404(TransitRoute, pk=route_pk)
    if request.method == 'POST':
        TransitSchedule.objects.create(
            route=route,
            day_of_week=int(request.POST['day_of_week']),
            departure_time=request.POST['departure_time'],
            origin_stop_id=request.POST['origin_stop'],
            destination_stop_id=request.POST['destination_stop'],
            estimated_duration_minutes=int(request.POST['estimated_duration_minutes']),
            frequency_minutes=int(request.POST['frequency_minutes']) if request.POST.get('frequency_minutes') else None,
        )
        messages.success(request, 'Schedule added.')
        return redirect('transit:route_detail', pk=route.pk)

    stops = route.stops.filter(is_active=True).order_by('sequence')
    return render(request, 'transit/schedule_form.html', {
        'route': route,
        'stops': stops,
        'days_of_week': TransitSchedule.DayOfWeek.choices,
    })


@login_required(login_url='login')
@require_POST
def schedule_delete(request, pk):
    if not _can_manage_transit(request.user):
        messages.error(request, 'Permission denied.')
        return redirect('transit:route_list')

    schedule = get_object_or_404(TransitSchedule, pk=pk)
    route_pk = schedule.route_id
    schedule.delete()
    messages.success(request, 'Schedule deleted.')
    return redirect('transit:route_detail', pk=route_pk)


@login_required(login_url='login')
def alert_create(request):
    if not _can_manage_transit(request.user):
        messages.error(request, 'Permission denied.')
        return redirect('transit:home')

    if request.method == 'POST':
        TransitAlert.objects.create(
            route_id=request.POST['route'] or None,
            agency_id=request.POST['agency'],
            title=request.POST['title'],
            message=request.POST['message'],
            severity=request.POST['severity'],
            starts_at=request.POST['starts_at'],
            ends_at=request.POST['ends_at'] or None,
            created_by=request.user,
        )
        messages.success(request, 'Alert created.')
        return redirect('transit:home')

    agencies = TransitAgency.objects.filter(is_active=True)
    routes = TransitRoute.objects.filter(is_active=True)
    return render(request, 'transit/alert_form.html', {
        'agencies': agencies,
        'routes': routes,
        'severities': TransitAlert.Severity.choices,
    })


@login_required(login_url='login')
@require_POST
def alert_delete(request, pk):
    if not _can_manage_transit(request.user):
        messages.error(request, 'Permission denied.')
        return redirect('transit:home')

    alert = get_object_or_404(TransitAlert, pk=pk)
    alert.delete()
    messages.success(request, 'Alert deleted.')
    return redirect('transit:home')

# Need to import models for use in transit_map
from django.db import models