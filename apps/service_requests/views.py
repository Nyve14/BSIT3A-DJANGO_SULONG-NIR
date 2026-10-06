from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import ServiceRequestForm
from .models import RequestUpdate, ServiceRequest


def _can_manage_requests(user):
    return user.is_staff or user.is_superuser


@login_required(login_url='login')
def request_list(request):
    query = request.GET.get('q', '').strip()
    status = request.GET.get('status', '').strip()

    requests = ServiceRequest.objects.select_related(
        'requester', 'assigned_to', 'department',
    )
    if not _can_manage_requests(request.user):
        requests = requests.filter(requester=request.user)
    if query:
        requests = requests.filter(
            Q(subject__icontains=query)
            | Q(description__icontains=query)
            | Q(reference__icontains=query)
            | Q(requester__username__icontains=query)
        )
    if status in ServiceRequest.Status.values:
        requests = requests.filter(status=status)

    paginator = Paginator(requests, 10)
    page = paginator.get_page(request.GET.get('page', 1))
    return render(request, 'service_requests/list.html', {
        'requests': page,
        'query': query,
        'selected_status': status,
        'statuses': ServiceRequest.Status.choices,
        'can_manage': _can_manage_requests(request.user),
    })


@login_required(login_url='login')
def request_create(request):
    if request.method == 'POST':
        form = ServiceRequestForm(request.POST)
        if form.is_valid():
            service_request = form.save(commit=False)
            service_request.requester = request.user
            service_request.save()
            RequestUpdate.objects.create(
                request=service_request,
                author=request.user,
                comment='Request submitted.',
                new_status=service_request.status,
            )
            messages.success(request, 'Your request has been submitted.')
            return redirect(
                'service_requests:detail',
                reference=service_request.reference,
            )
    else:
        form = ServiceRequestForm()

    return render(request, 'service_requests/form.html', {'form': form})


@login_required(login_url='login')
def request_detail(request, reference):
    queryset = ServiceRequest.objects.select_related(
        'requester', 'assigned_to', 'department',
    ).prefetch_related('updates__author')
    if not _can_manage_requests(request.user):
        queryset = queryset.filter(requester=request.user)
    service_request = get_object_or_404(queryset, reference=reference)
    return render(request, 'service_requests/detail.html', {
        'service_request': service_request,
        'can_manage': _can_manage_requests(request.user),
        'statuses': ServiceRequest.Status.choices,
    })


@login_required(login_url='login')
@require_POST
def request_update(request, reference):
    queryset = ServiceRequest.objects.all()
    if not _can_manage_requests(request.user):
        queryset = queryset.filter(requester=request.user)
    service_request = get_object_or_404(queryset, reference=reference)
    comment = request.POST.get('comment', '').strip()
    old_status = service_request.status

    if _can_manage_requests(request.user):
        new_status = request.POST.get('status', old_status)
        if new_status not in ServiceRequest.Status.values:
            messages.error(request, 'Choose a valid request status.')
            return redirect('service_requests:detail', reference=reference)
        service_request.status = new_status
        if new_status in {
            ServiceRequest.Status.COMPLETED,
            ServiceRequest.Status.REJECTED,
            ServiceRequest.Status.CANCELLED,
        }:
            service_request.resolved_at = timezone.now()
        elif old_status in {
            ServiceRequest.Status.COMPLETED,
            ServiceRequest.Status.REJECTED,
            ServiceRequest.Status.CANCELLED,
        }:
            service_request.resolved_at = None
    else:
        new_status = old_status
        if request.POST.get('action') == 'cancel':
            if old_status in {
                ServiceRequest.Status.COMPLETED,
                ServiceRequest.Status.REJECTED,
                ServiceRequest.Status.CANCELLED,
            }:
                messages.error(request, 'This request can no longer be cancelled.')
                return redirect('service_requests:detail', reference=reference)
            new_status = ServiceRequest.Status.CANCELLED
            service_request.status = new_status
            service_request.resolved_at = timezone.now()

    if not comment and old_status == new_status:
        messages.error(request, 'Add a comment or change the status before submitting.')
        return redirect('service_requests:detail', reference=reference)

    with transaction.atomic():
        if old_status != new_status:
            service_request.save(update_fields=['status', 'resolved_at', 'updated_at'])
        RequestUpdate.objects.create(
            request=service_request,
            author=request.user,
            comment=comment,
            previous_status=old_status if old_status != new_status else '',
            new_status=new_status if old_status != new_status else '',
        )

    messages.success(request, 'Request update saved.')
    return redirect('service_requests:detail', reference=reference)
