from collections import Counter
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from apps.concerns.models import ConcernReport, GeographicArea

User = get_user_model()

MAX_FAILED_ATTEMPTS = 5
LOCK_DURATION = timedelta(minutes=1)
INVALID_LOGIN_MESSAGE = 'Invalid username or password.'
LOCKED_MESSAGE = 'Too many failed attempts. Locked for 1 minute.'
NIR_PROVINCES = {
    'negros occidental': 'Negros Occidental',
    'negros oriental': 'Negros Oriental',
    'siquijor': 'Siquijor',
}
SETTLED_CONCERN_STATUSES = (
    ConcernReport.Status.RESOLVED,
    ConcernReport.Status.REJECTED,
    ConcernReport.Status.WITHDRAWN,
)


def _reset_lock_state(request):
    request.session['failed_attempts'] = 0
    request.session['lock_time'] = None


def _get_lock_state(request):
    failed_attempts = request.session.get('failed_attempts', 0)
    lock_time = request.session.get('lock_time')

    if not lock_time:
        return failed_attempts, None

    try:
        unlock_time = timezone.datetime.fromisoformat(lock_time)
    except (TypeError, ValueError):
        _reset_lock_state(request)
        return 0, None

    if timezone.now() < unlock_time:
        remaining = int((unlock_time - timezone.now()).total_seconds())
        return failed_attempts, remaining

    _reset_lock_state(request)
    return 0, None


def _set_lock_state(request):
    lock_until = timezone.now() + LOCK_DURATION
    request.session['failed_attempts'] = MAX_FAILED_ATTEMPTS
    request.session['lock_time'] = lock_until.isoformat()
    return int(LOCK_DURATION.total_seconds())


def _validate_registration_data(data):
    errors = {}

    username = data.get('username', '').strip()
    first_name = data.get('first_name', '').strip()
    last_name = data.get('last_name', '').strip()
    email = data.get('email', '').strip()
    password = data.get('password', '')
    confirm_password = data.get('confirm_password', '')

    if not username:
        errors['username'] = 'Username is required.'
    elif User.objects.filter(username=username).exists():
        errors['username'] = 'Username already taken.'

    if not first_name:
        errors['first_name'] = 'First name is required.'

    if not last_name:
        errors['last_name'] = 'Last name is required.'

    if not email:
        errors['email'] = 'Email is required.'
    else:
        try:
            validate_email(email)
        except ValidationError:
            errors['email'] = 'Enter a valid email address.'
        else:
            if User.objects.filter(email=email).exists():
                errors['email'] = 'Email already registered.'

    if not password:
        errors['password'] = 'Password is required.'
    elif len(password) < 8:
        errors['password'] = 'Password must be at least 8 characters.'
    else:
        try:
            validate_password(password)
        except ValidationError as exc:
            errors['password'] = ' '.join(exc.messages)

    if password != confirm_password:
        errors['confirm_password'] = 'Passwords do not match.'

    return errors


@require_http_methods(['GET', 'POST'])
def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    failed_attempts, remaining = _get_lock_state(request)
    if remaining is not None:
        messages.error(request, f'Too many failed attempts. Try again in {remaining} seconds.')
        return render(request, 'auth/login.html', {'locked': True, 'remaining': remaining})

    if request.method == 'GET':
        return render(request, 'auth/login.html')

    username = request.POST.get('username', '').strip()
    password = request.POST.get('password', '')
    user = authenticate(request, username=username, password=password)

    if user is not None:
        _reset_lock_state(request)
        login(request, user)
        return redirect('dashboard')

    failed_attempts += 1
    request.session['failed_attempts'] = failed_attempts
    if failed_attempts >= MAX_FAILED_ATTEMPTS:
        remaining = _set_lock_state(request)
        messages.error(request, LOCKED_MESSAGE)
        return render(request, 'auth/login.html', {'locked': True, 'remaining': remaining})

    remaining_attempts = MAX_FAILED_ATTEMPTS - failed_attempts
    messages.error(request, f'{INVALID_LOGIN_MESSAGE} {remaining_attempts} attempts remaining.')
    return render(request, 'auth/login.html')


def logout_view(request):
    logout(request)
    return redirect('login')


@login_required(login_url='login')
def home(request):
    return render(request, 'home.html')


@login_required(login_url='login')
@require_http_methods(['GET'])
def dashboard_live_concerns(request):
    reports = ConcernReport.objects.all()
    if not (request.user.is_staff or request.user.is_superuser):
        reports = reports.filter(reporter=request.user)

    summary = reports.aggregate(
        total=Count('pk'),
        resolved=Count('pk', filter=Q(status=ConcernReport.Status.RESOLVED)),
        closed=Count(
            'pk',
            filter=Q(status__in=(
                ConcernReport.Status.REJECTED,
                ConcernReport.Status.WITHDRAWN,
            )),
        ),
        active=Count('pk', filter=~Q(status__in=SETTLED_CONCERN_STATUSES)),
    )
    recent_reports = reports.select_related('area', 'category').order_by(
        '-updated_at', '-submitted_at',
    )[:10]

    response = JsonResponse({
        'summary': summary,
        'reports': [
            {
                'subject': report.subject,
                'category': report.category.name,
                'area': report.area.name,
                'status': report.status,
                'status_label': report.get_status_display(),
                'closed': report.status in SETTLED_CONCERN_STATUSES,
                'ai_category': report.ai_category,
                'ai_confidence': report.ai_confidence,
                'updated_at': report.updated_at.isoformat(),
            }
            for report in recent_reports
        ],
    })
    response['Cache-Control'] = 'no-store'
    return response


def _get_interactive_map_context(user):
    areas = {
        area_id: (parent_id, level, name, code)
        for area_id, parent_id, level, name, code in GeographicArea.objects.values_list(
            'id', 'parent_id', 'level', 'name', 'code',
        )
    }
    counts = Counter()
    barangay_counts = Counter()
    barangay_names = {}
    barangay_reports = {}
    unmapped_count = 0
    reports = ConcernReport.objects.all()
    if not (user.is_staff or user.is_superuser):
        reports = reports.filter(reporter=user)

    summary = reports.aggregate(
        total=Count('pk'),
        active=Count('pk', filter=~Q(status__in=SETTLED_CONCERN_STATUSES)),
        resolved=Count('pk', filter=Q(status=ConcernReport.Status.RESOLVED)),
    )

    # Settled concerns are cleared from the map, so they only feed the summary tiles.
    plotted_reports = reports.exclude(status__in=SETTLED_CONCERN_STATUSES)
    for report in plotted_reports.select_related('area').iterator():
        area_id = report.area_id
        status = report.status
        visited = set()
        while area_id in areas and area_id not in visited:
            visited.add(area_id)
            parent_id, level, name, code = areas[area_id]
            if level == GeographicArea.Level.BARANGAY:
                key = code or str(area_id)
                barangay_counts[(key, status)] += 1
                parent = areas.get(parent_id)
                barangay_names[key] = {
                    'name': name,
                    'municipality': parent[2] if parent else '',
                }
                barangay_reports.setdefault(key, []).append({
                    'reference': str(report.reference),
                    'subject': report.subject,
                    'status': status,
                    'status_label': report.get_status_display(),
                    'settled': status in SETTLED_CONCERN_STATUSES,
                })
            elif level == GeographicArea.Level.PROVINCE:
                province_name = name.casefold()
                if province_name in NIR_PROVINCES:
                    counts[(province_name, status)] += 1
                else:
                    unmapped_count += 1
                break
            area_id = parent_id
        else:
            unmapped_count += 1

    map_areas = [
        {
            'name': name,
            'counts': {
                status: counts[(name.casefold(), status)]
                for status in ConcernReport.Status.values
            },
        }
        for name in NIR_PROVINCES.values()
    ]
    map_barangays = []
    for key in sorted(barangay_names):
        settled = sum(
            count for (barangay_key, status), count in barangay_counts.items()
            if barangay_key == key and status in SETTLED_CONCERN_STATUSES
        )
        open_count = sum(
            count for (barangay_key, status), count in barangay_counts.items()
            if barangay_key == key and status not in SETTLED_CONCERN_STATUSES
        )
        map_barangays.append({
            'code': key,
            'name': barangay_names[key]['name'],
            'municipality': barangay_names[key]['municipality'],
            'open': open_count,
            'settled': settled,
            'reports': barangay_reports.get(key, []),
        })

    map_totals = {
        'total': summary['total'],
        'active': summary['active'],
        'resolved': summary['resolved'],
        'barangays': len(map_barangays),
        'municipalities': len({
            barangay['municipality']
            for barangay in map_barangays
            if barangay['municipality']
        }),
        'provinces': len(map_areas),
    }
    return {
        'map_areas': map_areas,
        'map_barangays': map_barangays,
        'map_totals': map_totals,
        'unmapped_report_count': unmapped_count,
        'can_view_all_concerns': user.is_staff or user.is_superuser,
    }


@login_required(login_url='login')
def interactive_map(request):
    return render(
        request,
        'interactive_map.html',
        _get_interactive_map_context(request.user),
    )


@require_http_methods(['GET', 'POST'])
def register_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'GET':
        return render(request, 'auth/register.html')

    form_data = {
        'username': request.POST.get('username', ''),
        'first_name': request.POST.get('first_name', ''),
        'last_name': request.POST.get('last_name', ''),
        'email': request.POST.get('email', ''),
        'password': request.POST.get('password', ''),
        'confirm_password': request.POST.get('confirm_password', ''),
    }

    errors = _validate_registration_data(form_data)
    if errors:
        return render(request, 'auth/register.html', {'errors': errors, 'form_data': form_data})

    user = User.objects.create_user(
        username=form_data['username'].strip(),
        first_name=form_data['first_name'].strip(),
        last_name=form_data['last_name'].strip(),
        email=form_data['email'].strip(),
        password=form_data['password'],
    )
    login(request, user)
    return redirect('dashboard')
