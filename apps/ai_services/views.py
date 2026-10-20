from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST

from .services import (
    classify_report,
    find_duplicates,
    suggest_response,
    CategoryPrediction,
    DuplicateMatch,
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
    """AI dashboard showing classification stats and insights."""
    from apps.concerns.models import ConcernReport, ConcernCategory
    from django.db.models import Count

    # Category distribution
    category_stats = ConcernReport.objects.values('category__name').annotate(
        count=Count('id')
    ).order_by('-count')[:10]

    # Status distribution
    status_stats = ConcernReport.objects.values('status').annotate(
        count=Count('id')
    ).order_by('-count')

    # Recent reports for AI analysis
    recent_reports = ConcernReport.objects.select_related('category').order_by('-submitted_at')[:20]

    # AI predictions for recent reports
    from .services import classify_report
    ai_insights = []
    for report in recent_reports:
        predictions = classify_report(report.subject, report.description)
        if predictions:
            ai_insights.append({
                'report': report,
                'predictions': predictions,
                'matches_category': report.category.name == predictions[0].category if predictions else False,
            })

    # Calculate match rate and average confidence
    match_rate = 0
    avg_confidence = 0
    if ai_insights:
        match_count = sum(1 for insight in ai_insights if insight['matches_category'])
        match_rate = (match_count / len(ai_insights)) * 100
        avg_confidence = sum(p['predictions'][0].confidence for insight in ai_insights for p in [insight['predictions'][0]]) / len(ai_insights)

    return render(request, 'ai_services/dashboard.html', {
        'category_stats': category_stats,
        'status_stats': status_stats,
        'ai_insights': ai_insights,
        'match_rate': match_rate,
        'avg_confidence': avg_confidence,
    })