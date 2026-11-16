from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Count, F
from django.db.models.functions import Lower
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET, require_POST

from .services import (
    classify_report,
    find_duplicates,
    suggest_response,
)


@login_required(login_url='login')
@require_POST
def api_classify_report(request):
    """API endpoint to classify a report."""
    subject = request.POST.get('subject', '')
    description = request.POST.get('description', '')

    if not subject or not description:
        return JsonResponse({'error': 'Subject and description required'}, status=400)

    predictions = classify_report(subject, description)
    return JsonResponse({
        'predictions': [
            {
                'category': p.category,
                'confidence': p.confidence,
                'subcategory': p.subcategory,
            }
            for p in predictions
        ]
    })


@login_required(login_url='login')
@require_POST
def api_find_duplicates(request):
    """API endpoint to find duplicate reports."""
    subject = request.POST.get('subject', '')
    description = request.POST.get('description', '')
    area_id = request.POST.get('area_id')

    if not subject or not description:
        return JsonResponse({'error': 'Subject and description required'}, status=400)

    # Get existing reports (excluding current user's draft)
    from apps.concerns.models import ConcernReport
    existing = ConcernReport.objects.exclude(
        reporter=request.user,
        status='draft' if hasattr(ConcernReport, 'status') else 'submitted'
    ).values('reference', 'subject', 'description', 'area_id')[:200]

    matches = find_duplicates(
        subject,
        description,
        list(existing),
        area_id=int(area_id) if area_id else None,
    )

    return JsonResponse({
        'duplicates': [
            {
                'report_id': m.report_id,
                'similarity': round(m.similarity, 3),
                'subject': m.subject,
            }
            for m in matches
        ]
    })


@login_required(login_url='login')
@require_POST
def api_suggest_response(request):
    """API endpoint to get response suggestions for staff."""
    subject = request.POST.get('subject', '')
    description = request.POST.get('description', '')
    current_status = request.POST.get('current_status', '')
    category = request.POST.get('category', '')

    if not subject or not description or not current_status:
        return JsonResponse({'error': 'Subject, description, and current_status required'}, status=400)

    suggestions = suggest_response(subject, description, current_status, category or None)
    return JsonResponse({
        'templates': suggestions['templates'],
        'suggested_category': suggestions['suggested_category'],
        'confidence': suggestions['confidence'],
        'suggested_subcategory': suggestions['suggested_subcategory'],
        'auto_assign_department': suggestions['auto_assign_department'],
    })


@login_required(login_url='login')
def ai_dashboard(request):
    """AI dashboard showing classification stats and automatically generated insights."""
    from apps.concerns.models import ConcernReport, GeographicArea
    from .services import analyze_concern_report

    # Backfill the automatic analysis for reports filed before this feature existed.
    pending = ConcernReport.objects.filter(ai_analyzed_at__isnull=True).order_by('-submitted_at')[:25]
    for report in pending:
        analyze_concern_report(report)

    snapshot = _build_insights_snapshot()
    snapshot['areas'] = GeographicArea.objects.filter(is_active=True)
    return render(request, 'ai_services/dashboard.html', snapshot)


@login_required(login_url='login')
@require_GET
@never_cache
def api_insights_snapshot(request):
    """Return a fresh, uncached snapshot for the live AI insights dashboard."""
    return JsonResponse(_build_insights_snapshot())


def _build_insights_snapshot():
    """Build dashboard metrics from persisted AI results and current reports."""
    from apps.concerns.models import ConcernReport
    from .services import generate_insights

    reports = ConcernReport.objects.all()
    analyzed = reports.filter(ai_analyzed_at__isnull=False)
    tagged = analyzed.exclude(ai_category='')

    total_analyzed = analyzed.count()
    auto_tagged = tagged.count()
    matched = tagged.annotate(
        actual_category=Lower('category__name'),
        predicted_category=Lower('ai_category'),
    ).filter(actual_category=F('predicted_category')).count()
    avg_confidence = tagged.aggregate(value=Avg('ai_confidence'))['value']

    insights = generate_insights()
    category_stats = [
        {'name': row['category__name'] or 'Uncategorized', 'count': row['count']}
        for row in reports.values('category__name').annotate(
            count=Count('id')
        ).order_by('-count')[:10]
    ]
    status_counts = dict(
        reports.values('status').annotate(count=Count('id')).values_list('status', 'count')
    )
    status_stats = [
        {'value': value, 'label': str(label), 'count': status_counts[value]}
        for value, label in ConcernReport.Status.choices
        if value in status_counts
    ]

    recent_analysis = []
    for report in analyzed.select_related('category').order_by('-submitted_at')[:20]:
        suggested_category = report.ai_category or ''
        recent_analysis.append({
            'subject': report.subject,
            'category': report.category.name,
            'suggested_category': suggested_category,
            'subcategory': report.ai_subcategory or '',
            'confidence': (
                round(report.ai_confidence * 100)
                if report.ai_confidence is not None else None
            ),
            'matches_category': (
                suggested_category.strip().casefold() == report.category.name.strip().casefold()
                if suggested_category else False
            ),
        })

    return {
        'total_reports': reports.count(),
        'total_analyzed': total_analyzed,
        'auto_tagged_count': auto_tagged,
        'match_rate': round((matched / auto_tagged) * 100) if auto_tagged else None,
        'avg_confidence': avg_confidence,
        'insight_summary': insights['summary'],
        'auto_insights': insights['insights'],
        'insights_generated_at': insights['generated_at'],
        'needs_review': insights['needs_review'],
        'category_stats': category_stats,
        'status_stats': status_stats,
        'recent_analysis': recent_analysis,
    }
