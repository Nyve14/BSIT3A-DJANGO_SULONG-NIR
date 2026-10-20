from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import AlertChannel, AlertDelivery, AlertPreference, AlertScope, AlertSeverity, EmergencyAlert, AlertTemplate


def _can_manage_alerts(user):
    return user.is_staff or user.is_superuser


@login_required(login_url='login')
def alert_list(request):
    alerts = EmergencyAlert.objects.select_related('created_by').annotate(
        delivery_count=Count('deliveries'),
    ).order_by('-created_at')

    q = request.GET.get('q', '').strip()
    severity = request.GET.get('severity')
    scope = request.GET.get('scope')
    status = request.GET.get('status')

    if q:
        alerts = alerts.filter(Q(title__icontains=q) | Q(message__icontains=q))
    if severity:
        alerts = alerts.filter(severity=severity)
    if scope:
        alerts = alerts.filter(scope=scope)
    if status == 'active':
        alerts = alerts.filter(is_active=True, expires_at__gte=timezone.now())
    elif status == 'expired':
        alerts = alerts.filter(expires_at__lt=timezone.now())
    elif status == 'scheduled':
        alerts = alerts.filter(sent_at__isnull=True, is_active=True)

    paginator = Paginator(alerts, 15)
    page = paginator.get_page(request.GET.get('page', 1))

    return render(request, 'alerts/list.html', {
        'alerts': page,
        'q': q,
        'selected_severity': severity,
        'selected_scope': scope,
        'selected_status': status,
        'severities': AlertSeverity.choices,
        'scopes': AlertScope.choices,
        'can_manage': _can_manage_alerts(request.user),
    })


@login_required(login_url='login')
def alert_create(request):
    if not _can_manage_alerts(request.user):
        messages.error(request, 'Permission denied.')
        return redirect('alerts:list')

    if request.method == 'POST':
        alert = EmergencyAlert.objects.create(
            title=request.POST['title'],
            message=request.POST['message'],
            severity=request.POST['severity'],
            scope=request.POST['scope'],
            channels=request.POST.getlist('channels') or ['in_app'],
            expires_at=request.POST['expires_at'] or None,
            created_by=request.user,
        )
        # Handle target areas
        area_ids = request.POST.getlist('target_areas')
        if area_ids:
            alert.target_areas.set(area_ids)
        # Handle target users
        user_ids = request.POST.getlist('target_users')
        if user_ids:
            alert.target_users.set(user_ids)

        messages.success(request, 'Emergency alert created.')
        return redirect('alerts:detail', pk=alert.pk)

    from apps.concerns.models import GeographicArea
    areas = GeographicArea.objects.filter(is_active=True).exclude(level='region').select_related('parent')
    users = __import__('django.contrib.auth', fromlist=['get_user_model']).get_user_model().objects.filter(is_active=True).order_by('username')

    return render(request, 'alerts/form.html', {
        'areas': areas,
        'users': users,
        'severities': AlertSeverity.choices,
        'scopes': AlertScope.choices,
        'channels': AlertChannel.choices,
        'templates': AlertTemplate.objects.filter(is_active=True),
    })


@login_required(login_url='login')
def alert_detail(request, pk):
    alert = get_object_or_404(
        EmergencyAlert.objects.select_related('created_by').prefetch_related('target_areas', 'target_users'),
        pk=pk,
    )
    deliveries = alert.deliveries.select_related('user').order_by('-created_at')[:50]

    delivery_stats = alert.deliveries.values('channel', 'status').annotate(count=Count('id'))

    return render(request, 'alerts/detail.html', {
        'alert': alert,
        'deliveries': deliveries,
        'delivery_stats': delivery_stats,
        'can_manage': _can_manage_alerts(request.user),
    })


@login_required(login_url='login')
@require_POST
def alert_send(request, pk):
    if not _can_manage_alerts(request.user):
        messages.error(request, 'Permission denied.')
        return redirect('alerts:list')

    alert = get_object_or_404(EmergencyAlert, pk=pk)

    # Determine target users
    users = set()
    if alert.scope == EmergencyAlert.Scope.SYSTEM_WIDE:
        users.update(__import__('django.contrib.auth', fromlist=['get_user_model']).get_user_model().objects.filter(is_active=True))
    elif alert.scope == EmergencyAlert.Scope.PROVINCE:
        for area in alert.target_areas.filter(level='province'):
            users.update(area.get_all_descendant_users())
    elif alert.scope == EmergencyAlert.Scope.CITY_MUNICIPALITY:
        for area in alert.target_areas.filter(level='city_municipality'):
            users.update(area.get_all_descendant_users())
    elif alert.scope == EmergencyAlert.Scope.BARANGAY:
        for area in alert.target_areas.filter(level='barangay'):
            users.update(area.get_all_descendant_users())
    elif alert.scope == EmergencyAlert.Scope.CUSTOM:
        users.update(alert.target_users.all())

    # Create deliveries
    deliveries_to_create = []
    for user in users:
        prefs, _ = AlertPreference.objects.get_or_create(user=user)
        severity_order = {s[0]: i for i, s in enumerate(AlertSeverity.choices)}
        if severity_order[alert.severity] < severity_order[prefs.min_severity]:
            continue

        for channel in alert.channels:
            if channel == 'in_app' and not prefs.receive_in_app:
                continue
            if channel == 'email' and not prefs.receive_email:
                continue
            if channel == 'sms' and not prefs.receive_sms:
                continue
            if channel == 'push' and not prefs.receive_push:
                continue

            deliveries_to_create.append(AlertDelivery(
                alert=alert,
                user=user,
                channel=channel,
                status=AlertDelivery.Status.PENDING,
            ))

    AlertDelivery.objects.bulk_create(deliveries_to_create, ignore_conflicts=True)

    # TODO: Actually send via channels (email, SMS, push)
    # For now, mark in-app as sent
    AlertDelivery.objects.filter(alert=alert, channel='in_app', status=AlertDelivery.Status.PENDING).update(
        status=AlertDelivery.Status.SENT,
        sent_at=timezone.now(),
    )

    alert.sent_at = timezone.now()
    alert.save(update_fields=['sent_at'])

    messages.success(request, f'Alert sent to {len(users)} users via {len(alert.channels)} channels.')
    return redirect('alerts:detail', pk=alert.pk)


@login_required(login_url='login')
@require_POST
def alert_mark_read(request, pk):
    delivery = get_object_or_404(AlertDelivery, pk=pk, user=request.user)
    if delivery.status != AlertDelivery.Status.READ:
        delivery.status = AlertDelivery.Status.READ
        delivery.read_at = timezone.now()
        delivery.save(update_fields=['status', 'read_at'])
    return JsonResponse({'status': 'ok'})


@login_required(login_url='login')
def user_alerts(request):
    """List alerts for the current user."""
    deliveries = AlertDelivery.objects.filter(
        user=request.user,
        alert__is_active=True,
    ).select_related('alert', 'alert__created_by').order_by('-alert__created_at')

    q = request.GET.get('q', '').strip()
    if q:
        deliveries = deliveries.filter(Q(alert__title__icontains=q) | Q(alert__message__icontains=q))

    unread_only = request.GET.get('unread') == '1'
    if unread_only:
        deliveries = deliveries.exclude(status=AlertDelivery.Status.READ)

    paginator = Paginator(deliveries, 20)
    page = paginator.get_page(request.GET.get('page', 1))

    return render(request, 'alerts/user_alerts.html', {
        'deliveries': page,
        'q': q,
        'unread_only': unread_only,
    })


@login_required(login_url='login')
def user_preferences(request):
    prefs, _ = AlertPreference.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        prefs.receive_in_app = 'receive_in_app' in request.POST
        prefs.receive_email = 'receive_email' in request.POST
        prefs.receive_sms = 'receive_sms' in request.POST
        prefs.receive_push = 'receive_push' in request.POST
        prefs.min_severity = request.POST.get('min_severity', prefs.min_severity)
        prefs.quiet_hours_start = request.POST.get('quiet_hours_start') or None
        prefs.quiet_hours_end = request.POST.get('quiet_hours_end') or None
        prefs.save()
        messages.success(request, 'Preferences updated.')
        return redirect('alerts:user_preferences')

    return render(request, 'alerts/preferences.html', {
        'prefs': prefs,
        'severities': AlertSeverity.choices,
    })


def alert_count(request):
    """API endpoint for unread alert count (for navbar badge)."""
    if not request.user.is_authenticated:
        return JsonResponse({'count': 0})
    count = AlertDelivery.objects.filter(
        user=request.user,
        status__in=[AlertDelivery.Status.PENDING, AlertDelivery.Status.SENT, AlertDelivery.Status.DELIVERED],
        alert__is_active=True,
    ).count()
    return JsonResponse({'count': count})