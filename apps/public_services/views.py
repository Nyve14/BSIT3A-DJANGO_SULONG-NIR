from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Avg, Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import ServiceForm, ServiceReviewForm, ServiceSearchForm
from .models import Service, ServiceCategory, ServiceReview


def _can_manage_services(user):
    return user.is_staff or user.is_superuser


def service_list(request):
    form = ServiceSearchForm(request.GET)
    services = Service.objects.select_related(
        'category', 'barangay', 'barangay__parent', 'barangay__parent__parent'
    ).annotate(
        avg_rating=Avg('reviews__rating'),
        review_count=Count('reviews'),
    ).filter(status=Service.Status.ACTIVE)

    if form.is_valid():
        q = form.cleaned_data.get('q', '').strip()
        category = form.cleaned_data.get('category')
        barangay = form.cleaned_data.get('barangay')
        status = form.cleaned_data.get('status')

        if q:
            services = services.filter(
                Q(name__icontains=q)
                | Q(description__icontains=q)
                | Q(address__icontains=q)
                | Q(category__name__icontains=q)
            )
        if category:
            services = services.filter(category=category)
        if barangay:
            services = services.filter(barangay=barangay)
        if status:
            services = services.filter(status=status)

    services = services.order_by('name')
    paginator = Paginator(services, 12)
    page = paginator.get_page(request.GET.get('page', 1))

    # Get categories for sidebar with recursive counts (1 level deep)
    categories = ServiceCategory.objects.filter(
        is_active=True, parent__isnull=True
    ).annotate(
        direct_count=Count('services', filter=Q(services__status=Service.Status.ACTIVE), distinct=True),
        child_count=Count('children__services', filter=Q(children__services__status=Service.Status.ACTIVE), distinct=True)
    ).order_by('sort_order', 'name')

    # Combine counts
    for cat in categories:
        cat.service_count = cat.direct_count + cat.child_count

    return render(request, 'public_services/list.html', {
        'services': page,
        'form': form,
        'categories': categories,
        'can_manage': _can_manage_services(request.user),
    })


@login_required(login_url='login')
def service_create(request):
    if not _can_manage_services(request.user):
        messages.error(request, 'You do not have permission to add services.')
        return redirect('public_services:list')

    if request.method == 'POST':
        form = ServiceForm(request.POST)
        if form.is_valid():
            service = form.save(commit=False)
            service.created_by = request.user
            service.save()
            messages.success(request, 'Service added successfully.')
            return redirect('public_services:detail', slug=service.slug)
    else:
        form = ServiceForm()
    return render(request, 'public_services/form.html', {'form': form})


def service_detail(request, slug):
    service = get_object_or_404(
        Service.objects.select_related(
            'category', 'category__parent', 'barangay', 'barangay__parent', 'barangay__parent__parent', 'created_by'
        ).annotate(
            avg_rating=Avg('reviews__rating'),
            review_count=Count('reviews'),
        ),
        slug=slug,
    )
    reviews = service.reviews.select_related('user').order_by('-created_at')[:10]
    user_review = None
    if request.user.is_authenticated:
        user_review = reviews.filter(user=request.user).first()

    review_form = ServiceReviewForm() if request.user.is_authenticated and not user_review else None

    return render(request, 'public_services/detail.html', {
        'service': service,
        'reviews': reviews,
        'user_review': user_review,
        'review_form': review_form,
        'can_manage': _can_manage_services(request.user),
    })


@login_required(login_url='login')
@require_POST
def service_add_review(request, slug):
    service = get_object_or_404(Service, slug=slug, status=Service.Status.ACTIVE)
    if ServiceReview.objects.filter(service=service, user=request.user).exists():
        messages.error(request, 'You have already reviewed this service.')
        return redirect('public_services:detail', slug=slug)

    form = ServiceReviewForm(request.POST)
    if form.is_valid():
        review = form.save(commit=False)
        review.service = service
        review.user = request.user
        review.save()
        messages.success(request, 'Thank you for your review!')
    else:
        messages.error(request, 'Please provide a rating.')
    return redirect('public_services:detail', slug=slug)


@login_required(login_url='login')
def service_edit(request, slug):
    if not _can_manage_services(request.user):
        messages.error(request, 'You do not have permission to edit services.')
        return redirect('public_services:list')

    service = get_object_or_404(Service, slug=slug)
    if request.method == 'POST':
        form = ServiceForm(request.POST, instance=service)
        if form.is_valid():
            form.save()
            messages.success(request, 'Service updated successfully.')
            return redirect('public_services:detail', slug=service.slug)
    else:
        form = ServiceForm(instance=service)
    return render(request, 'public_services/form.html', {'form': form, 'service': service})


@login_required(login_url='login')
@require_POST
def service_delete(request, slug):
    if not _can_manage_services(request.user):
        messages.error(request, 'You do not have permission to delete services.')
        return redirect('public_services:list')

    service = get_object_or_404(Service, slug=slug)
    service.delete()
    messages.success(request, 'Service deleted.')
    return redirect('public_services:list')


def service_category(request, category_slug):
    category = get_object_or_404(ServiceCategory, slug=category_slug, is_active=True)
    
    # Include children categories if this is a parent
    category_ids = [category.id]
    if not category.parent:
        category_ids.extend(category.children.values_list('id', flat=True))

    services = Service.objects.select_related(
        'category', 'barangay', 'barangay__parent', 'barangay__parent__parent'
    ).filter(
        category_id__in=category_ids,
        status=Service.Status.ACTIVE,
    ).annotate(
        avg_rating=Avg('reviews__rating'),
        review_count=Count('reviews'),
    ).order_by('name')

    paginator = Paginator(services, 12)
    page = paginator.get_page(request.GET.get('page', 1))

    # Get categories for sidebar with recursive counts (1 level deep)
    categories = ServiceCategory.objects.filter(
        is_active=True, parent__isnull=True
    ).annotate(
        direct_count=Count('services', filter=Q(services__status=Service.Status.ACTIVE), distinct=True),
        child_count=Count('children__services', filter=Q(children__services__status=Service.Status.ACTIVE), distinct=True)
    ).order_by('sort_order', 'name')

    # Combine counts
    for cat in categories:
        cat.service_count = cat.direct_count + cat.child_count

    return render(request, 'public_services/category.html', {
        'category': category,
        'services': page,
        'categories': categories,
    })


def service_map(request):
    """Return GeoJSON of active services for map display."""
    from django.http import JsonResponse
    services = Service.objects.filter(
        status=Service.Status.ACTIVE,
        latitude__isnull=False,
        longitude__isnull=False,
    ).select_related('category', 'barangay').values(
        'reference', 'name', 'slug', 'category__name', 'category__icon',
        'address', 'barangay__name', 'latitude', 'longitude', 'phone', 'website',
        'hours_monday', 'hours_tuesday', 'hours_wednesday', 'hours_thursday',
        'hours_friday', 'hours_saturday', 'hours_sunday', 'status',
    )
    features = []
    for svc in services:
        features.append({
            'type': 'Feature',
            'geometry': {
                'type': 'Point',
                'coordinates': [float(svc['longitude']), float(svc['latitude'])],
            },
            'properties': {
                'reference': str(svc['reference']),
                'name': svc['name'],
                'slug': svc['slug'],
                'category': svc['category__name'],
                'category_icon': svc['category__icon'] or 'fas fa-map-marker-alt',
                'address': svc['address'],
                'barangay': svc['barangay__name'],
                'phone': svc['phone'],
                'website': svc['website'],
                'hours': {
                    'monday': svc['hours_monday'],
                    'tuesday': svc['hours_tuesday'],
                    'wednesday': svc['hours_wednesday'],
                    'thursday': svc['hours_thursday'],
                    'friday': svc['hours_friday'],
                    'saturday': svc['hours_saturday'],
                    'sunday': svc['hours_sunday'],
                },
            },
        })
    return JsonResponse({
        'type': 'FeatureCollection',
        'features': features,
    })