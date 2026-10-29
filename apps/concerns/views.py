from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.utils.formats import date_format
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET, require_POST

from apps.ai_services.services import analyze_concern_report

from .forms import ConcernReportForm, ConcernUpdateForm
from .models import (
    ConcernReport,
    GeographicArea,
    ReportAttachment,
    ReportAssignmentHistory,
    ReportStatusHistory,
)


@login_required(login_url='login')
def api_get_child_areas(request):
    """API endpoint to get child geographic areas for cascading dropdowns."""
    parent_id = request.GET.get('parent_id')
    if not parent_id:
        return JsonResponse({'areas': []})
    
    areas = GeographicArea.objects.filter(
        parent_id=parent_id,
        is_active=True
    ).values('id', 'name', 'level')
    
    return JsonResponse({'areas': list(areas)})


def _can_manage_concerns(user):
    return user.is_staff or user.is_superuser


@login_required(login_url='login')
def concern_list(request):
    query = request.GET.get('q', '').strip()
    status = request.GET.get('status', '').strip()
    reports = ConcernReport.objects.select_related(
        'reporter', 'department', 'assigned_to', 'area', 'category',
    )
    if _can_manage_concerns(request.user):
        reports = reports.exclude(status=ConcernReport.Status.WITHDRAWN)
    else:
        reports = reports.filter(reporter=request.user)
    if query:
        reports = reports.filter(
            Q(subject__icontains=query)
            | Q(description__icontains=query)
            | Q(reference__icontains=query)
            | Q(location_details__icontains=query)
        )
    if status in ConcernReport.Status.values:
        reports = reports.filter(status=status)

    page = Paginator(reports, 10).get_page(request.GET.get('page', 1))
    return render(request, 'concerns/list.html', {
        'reports': page,
        'query': query,
        'selected_status': status,
        'statuses': ConcernReport.Status.choices,
        'can_manage': _can_manage_concerns(request.user),
    })


@login_required(login_url='login')
def concern_create(request):
    if request.method == 'POST':
        form = ConcernReportForm(request.POST, request.FILES)
        if form.is_valid():
            with transaction.atomic():
                report = form.save(commit=False)
                report.reporter = request.user
                report.save()
                # Handle attachments
                for f in request.FILES.getlist('attachments'):
                    ReportAttachment.objects.create(
                        report=report,
                        uploaded_by=request.user,
                        file=f,
                        original_name=f.name,
                        content_type=f.content_type or '',
                        size_bytes=f.size,
                    )
                ReportStatusHistory.objects.create(
                    report=report,
                    actor=request.user,
                    new_status=report.status,
                    comment='Concern submitted.',
                )
                # Automatic AI analysis: tag the report and flag duplicates.
                analyze_concern_report(report)
            if report.ai_duplicate_of_id:
                messages.info(
                    request,
                    'Automatic analysis flagged this report as a possible duplicate '
                    f'of “{report.ai_duplicate_of.subject}”.',
                )
            messages.success(request, 'Your concern has been submitted.')
            return redirect('reports:detail', reference=report.reference)
    else:
        form = ConcernReportForm()
    return render(request, 'concerns/form.html', {'form': form})


@login_required(login_url='login')
def concern_detail(request, reference):
    reports = ConcernReport.objects.select_related(
        'reporter', 'department', 'assigned_to', 'area', 'category',
    ).prefetch_related(
        'status_history__actor', 'assignment_history', 'attachments__uploaded_by'
    )
    if not _can_manage_concerns(request.user):
        reports = reports.filter(reporter=request.user)
    report = get_object_or_404(reports, reference=reference)
    updates = report.status_history.all()
    if not _can_manage_concerns(request.user):
        updates = updates.filter(visibility=ReportStatusHistory.Visibility.PUBLIC)
    return render(request, 'concerns/detail.html', {
        'report': report,
        'updates': updates,
        'attachments': report.attachments.all(),
        'can_manage': _can_manage_concerns(request.user),
        'form': ConcernUpdateForm(
            is_staff=_can_manage_concerns(request.user),
            initial={
                'status': report.status,
                'assigned_to': report.assigned_to_id,
            },
        ),
    })


@login_required(login_url='login')
@require_GET
@never_cache
def concern_updates(request, reference):
    reports = ConcernReport.objects.select_related(
        'reporter', 'assigned_to',
    )
    if not _can_manage_concerns(request.user):
        reports = reports.filter(reporter=request.user)
    report = get_object_or_404(reports, reference=reference)

    updates = report.status_history.select_related('actor')
    if not _can_manage_concerns(request.user):
        updates = updates.filter(
            visibility=ReportStatusHistory.Visibility.PUBLIC,
        )

    assigned_to = report.assigned_to
    return JsonResponse({
        'updates_html': render_to_string(
            'concerns/_updates.html',
            {'updates': updates},
            request=request,
        ),
        'status_display': report.get_status_display(),
        'assigned_to': (
            assigned_to.get_full_name() or assigned_to.username
            if assigned_to else 'Unassigned'
        ),
        'resolved_at': (
            date_format(
                timezone.localtime(report.resolved_at),
                'M j, Y · g:i a',
            )
            if report.resolved_at else '—'
        ),
    })


@login_required(login_url='login')
@require_POST
def concern_update(request, reference):
    is_staff = _can_manage_concerns(request.user)
    reports = ConcernReport.objects.all()
    if not is_staff:
        reports = reports.filter(reporter=request.user)
    report = get_object_or_404(reports, reference=reference)
    form = ConcernUpdateForm(request.POST, is_staff=is_staff)
    if not form.is_valid():
        messages.error(request, 'Please correct the update form.')
        return redirect('reports:detail', reference=reference)

    comment = form.cleaned_data['comment'].strip()
    old_status = report.status
    old_assigned_to_id = report.assigned_to_id
    new_status = old_status

    if is_staff:
        new_status = form.cleaned_data['status'] or old_status
        new_assignee = form.cleaned_data['assigned_to']
        report.assigned_to = new_assignee
    else:
        new_assignee = report.assigned_to
        if request.POST.get('action') == 'withdraw':
            if report.status in {
                ConcernReport.Status.RESOLVED,
                ConcernReport.Status.REJECTED,
                ConcernReport.Status.WITHDRAWN,
            }:
                messages.error(request, 'This concern can no longer be withdrawn.')
                return redirect('reports:detail', reference=reference)
            new_status = ConcernReport.Status.WITHDRAWN

    assignment_changed = (
        new_assignee.pk if new_assignee else None
    ) != old_assigned_to_id
    status_changed = new_status != old_status
    if not comment and not status_changed and not assignment_changed:
        messages.error(request, 'Add an update or make a change before submitting.')
        return redirect('reports:detail', reference=reference)

    with transaction.atomic():
        report.status = new_status
        if new_status in {
            ConcernReport.Status.RESOLVED,
            ConcernReport.Status.REJECTED,
            ConcernReport.Status.WITHDRAWN,
        }:
            report.resolved_at = report.resolved_at or timezone.now()
        elif status_changed:
            report.resolved_at = None
        report.save()

        if assignment_changed:
            ReportAssignmentHistory.objects.filter(
                report=report,
                ended_at__isnull=True,
            ).update(ended_at=timezone.now())
            if report.department_id or report.assigned_to_id:
                ReportAssignmentHistory.objects.create(
                    report=report,
                    department=report.department,
                    assignee=report.assigned_to,
                    assigned_by=request.user,
                )

        if status_changed or comment:
            ReportStatusHistory.objects.create(
                report=report,
                actor=request.user,
                old_status=old_status if status_changed else '',
                new_status=new_status if status_changed else '',
                comment=comment,
                visibility=(
                    ReportStatusHistory.Visibility.STAFF_ONLY
                    if is_staff and form.cleaned_data.get('staff_only')
                    else ReportStatusHistory.Visibility.PUBLIC
                ),
            )

    messages.success(request, 'Concern update saved.')
    return redirect('reports:detail', reference=reference)


@login_required(login_url='login')
@require_POST
def concern_delete(request, reference):
    report = get_object_or_404(
        ConcernReport.objects.prefetch_related('attachments'),
        reference=reference,
        reporter=request.user,
        status=ConcernReport.Status.WITHDRAWN,
    )

    with transaction.atomic():
        for attachment in report.attachments.all():
            attachment.file.delete(save=False)
        report.delete()

    messages.success(request, 'Withdrawn concern deleted.')
    return redirect('reports:list')
