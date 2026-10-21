import re
import json
from datetime import timedelta
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from difflib import SequenceMatcher


@dataclass
class CategoryPrediction:
    category: str
    confidence: float
    subcategory: Optional[str] = None


@dataclass
class DuplicateMatch:
    report_id: str
    similarity: float
    subject: str


class ReportClassifier:
    """Smart categorization of reports based on text analysis."""

    CATEGORY_KEYWORDS = {
        'Roads & Infrastructure': {
            'keywords': ['pothole', 'road damage', 'bridge', 'sidewalk', 'street light', 'drainage', 'flood', 'traffic sign', 'marking', 'culvert', 'erosion', 'crack', 'pavement', 'asphalt', 'concrete', 'manhole', 'gutter'],
            'subcategories': {
                'Potholes & Road Damage': ['pothole', 'crack', 'pavement', 'asphalt', 'road damage', 'eroded'],
                'Bridge & Culvert Issues': ['bridge', 'culvert'],
                'Sidewalk & Pedestrian Path': ['sidewalk', 'pedestrian', 'ramp', 'crosswalk'],
                'Street Lighting': ['street light', 'lamp post', 'lighting', 'dark'],
                'Drainage & Flooding': ['drainage', 'flood', 'clogged drain', 'water logging', 'gutter'],
                'Traffic Signs & Markings': ['traffic sign', 'marking', 'signage', 'stop sign', 'yield'],
            }
        },
        'Utilities': {
            'keywords': ['water', 'electricity', 'power', 'internet', 'phone', 'signal', 'outage', 'no water', 'low pressure', 'voltage', 'wire', 'cable', 'transformer', 'meter'],
            'subcategories': {
                'Water Supply': ['water', 'no water', 'low pressure', 'contaminated', 'pipe burst', 'leak'],
                'Electricity': ['electricity', 'power', 'outage', 'voltage', 'wire', 'transformer', 'brownout', 'blackout'],
                'Telecommunications': ['internet', 'phone', 'signal', 'cable', 'wifi', 'broadband', 'landline'],
            }
        },
        'Public Safety': {
            'keywords': ['crime', 'theft', 'robbery', 'assault', 'vandalism', 'accident', 'traffic accident', 'fire', 'fire hazard', 'stray dog', 'animal', 'suspicious', 'drug', 'violence'],
            'subcategories': {
                'Crime & Security': ['crime', 'theft', 'robbery', 'assault', 'vandalism', 'suspicious', 'drug', 'burglary'],
                'Traffic Accidents': ['traffic accident', 'vehicle accident', 'hit and run', 'collision', 'crash'],
                'Fire Hazards': ['fire', 'fire hazard', 'burning', 'smoke', 'flammable'],
                'Animal Control': ['stray dog', 'stray cat', 'livestock', 'animal', 'dog bite'],
            }
        },
        'Environment': {
            'keywords': ['flood', 'garbage', 'trash', 'waste', 'pollution', 'smoke', 'chemical', 'spill', 'tree', 'vegetation', 'illegal dumping', 'recycling', 'compost'],
            'subcategories': {
                'Flooding & Drainage': ['flood', 'flooding', 'drainage', 'water logging'],
                'Garbage & Waste': ['garbage', 'trash', 'waste', 'illegal dumping', 'uncollected', 'rubbish'],
                'Air & Water Pollution': ['pollution', 'smoke', 'chemical', 'spill', 'contaminated water', 'air quality'],
                'Trees & Vegetation': ['tree', 'vegetation', 'fallen tree', 'overgrown', 'branch'],
            }
        },
        'Health & Sanitation': {
            'keywords': ['dengue', 'covid', 'vaccine', 'vaccination', 'clinic', 'hospital', 'health center', 'sanitation', 'toilet', 'sewage', 'medicine', 'outbreak', 'disease'],
            'subcategories': {
                'Disease Surveillance': ['dengue', 'covid', 'outbreak', 'disease', 'case', 'infected'],
                'Vaccination Programs': ['vaccine', 'vaccination', 'immunization', 'shot'],
                'Sanitation & Toilets': ['sanitation', 'toilet', 'sewage', 'septic', 'public toilet'],
                'Health Center Services': ['clinic', 'hospital', 'health center', 'medicine', 'doctor', 'nurse'],
            }
        },
        'Transportation': {
            'keywords': ['bus', 'jeepney', 'tricycle', 'terminal', 'route', 'schedule', 'fare', 'transport', 'commute', 'pedicab', 'multicab', 'van'],
            'subcategories': {
                'Public Transit': ['bus', 'route', 'schedule', 'terminal', 'van'],
                'Tricycle & Pedicab': ['tricycle', 'pedicab', 'terminal'],
                'Road Accessibility': ['road closure', 'construction', 'detour', 'blocked', 'impassable'],
            }
        },
        'Government Services': {
            'keywords': ['permit', 'license', 'certificate', 'clearance', 'id', 'identification', 'birth certificate', 'marriage', 'death', 'business permit', 'mayor permit', '4ps', 'senior', 'pwd', 'benefit', 'aid', 'assistance'],
            'subcategories': {
                'Barangay Certificates': ['clearance', 'residency', 'indigency', 'barangay certificate'],
                'Business Permits': ['business permit', 'mayor permit', 'renewal', 'license'],
                'Civil Registry': ['birth certificate', 'marriage certificate', 'death certificate', 'psa'],
                'Social Services': ['4ps', 'senior', 'pwd', 'benefit', 'aid', 'assistance', 'pension'],
            }
        },
        'Education': {
            'keywords': ['school', 'classroom', 'enrollment', 'scholarship', 'teacher', 'student', 'education', 'facility', 'repair', 'library', 'computer', 'laboratory'],
            'subcategories': {
                'School Facilities': ['school', 'classroom', 'facility', 'repair', 'building', 'roof', 'ceiling'],
                'Enrollment & Scholarships': ['enrollment', 'scholarship', 'admission', 'financial aid', 'grant'],
                'School Safety': ['safety', 'security', 'emergency', 'drill', 'fire drill', 'earthquake'],
            }
        },
    }

    def __init__(self):
        self._compile_patterns()

    def _compile_patterns(self):
        """Pre-compile keyword patterns for faster matching."""
        for cat_name, cat_data in self.CATEGORY_KEYWORDS.items():
            cat_data['pattern'] = re.compile(
                r'\b(' + '|'.join(re.escape(kw) for kw in cat_data['keywords']) + r')\b',
                re.IGNORECASE
            )
            cat_data['sub_patterns'] = {}
            for sub_name, sub_keywords in cat_data['subcategories'].items():
                cat_data['sub_patterns'][sub_name] = re.compile(
                    r'\b(' + '|'.join(re.escape(kw) for kw in sub_keywords) + r')\b',
                    re.IGNORECASE
                )

    def predict(self, subject: str, description: str) -> List[CategoryPrediction]:
        """Predict categories for a report based on subject and description."""
        text = f"{subject} {description}".lower()
        predictions = []

        for cat_name, cat_data in self.CATEGORY_KEYWORDS.items():
            matches = cat_data['pattern'].findall(text)
            if matches:
                confidence = min(len(matches) * 0.15, 1.0)

                # Check subcategories
                best_sub = None
                best_sub_confidence = 0
                for sub_name, sub_pattern in cat_data['sub_patterns'].items():
                    sub_matches = sub_pattern.findall(text)
                    if sub_matches:
                        sub_conf = min(len(sub_matches) * 0.2, 1.0)
                        if sub_conf > best_sub_confidence:
                            best_sub_confidence = sub_conf
                            best_sub = sub_name

                predictions.append(CategoryPrediction(
                    category=cat_name,
                    confidence=confidence,
                    subcategory=best_sub,
                ))

        # Sort by confidence
        predictions.sort(key=lambda p: p.confidence, reverse=True)
        return predictions[:3]  # Return top 3


class DuplicateDetector:
    """Detect potential duplicate reports."""

    def __init__(self, similarity_threshold: float = 0.75):
        self.threshold = similarity_threshold

    def _similarity(self, a: str, b: str) -> float:
        """Calculate text similarity using SequenceMatcher."""
        return SequenceMatcher(None, a.lower(), b.lower()).ratio()

    def find_duplicates(
        self,
        subject: str,
        description: str,
        existing_reports: List[Dict[str, Any]],
        area_id: Optional[int] = None
    ) -> List[DuplicateMatch]:
        """Find potential duplicate reports."""
        text = f"{subject} {description}"
        matches = []

        for report in existing_reports:
            # Skip if different area (optional filter)
            if area_id and report.get('area_id') != area_id:
                continue

            existing_text = f"{report['subject']} {report.get('description', '')}"
            similarity = self._similarity(text, existing_text)

            if similarity >= self.threshold:
                matches.append(DuplicateMatch(
                    report_id=report['reference'],
                    similarity=similarity,
                    subject=report['subject'],
                ))

        matches.sort(key=lambda m: m.similarity, reverse=True)
        return matches[:5]


class ResponseSuggester:
    """Generate response suggestions for staff."""

    TEMPLATES = {
        'acknowledgment': [
            "Thank you for reporting this issue. We have received your report and will investigate.",
            "Thank you for your report. Our team has been notified and will look into this matter.",
            "We appreciate you reporting this. Our staff will review and take appropriate action.",
        ],
        'in_progress': [
            "Our team is currently investigating this issue. We will provide an update soon.",
            "Work has begun on addressing this concern. We'll keep you informed of progress.",
            "This issue is now being actively addressed. Estimated resolution time: {timeframe}.",
        ],
        'resolved': [
            "This issue has been resolved. Thank you for your patience.",
            "The reported problem has been fixed. Please let us know if you notice any further issues.",
            "We have completed the necessary work. The issue should now be resolved.",
        ],
        'needs_info': [
            "We need more information to proceed. Could you please provide {details}?",
            "To help us resolve this faster, could you clarify {details}?",
            "Additional details needed: {details}. Please update your report when possible.",
        ],
        'referral': [
            "This issue has been referred to the {department} for appropriate action.",
            "Your report has been forwarded to {department} who handles this type of concern.",
            "We've escalated this to {department} for their expertise and action.",
        ],
    }

    def __init__(self):
        self.classifier = ReportClassifier()

    def suggest_response(
        self,
        report_subject: str,
        report_description: str,
        current_status: str,
        category: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Generate response suggestions based on report content and status."""
        predictions = self.classifier.predict(report_subject, report_description)
        top_category = predictions[0].category if predictions else category

        suggestions = {
            'templates': self.TEMPLATES.get(current_status, self.TEMPLATES['acknowledgment']),
            'suggested_category': top_category,
            'confidence': predictions[0].confidence if predictions else 0,
            'suggested_subcategory': predictions[0].subcategory if predictions else None,
            'auto_assign_department': self._suggest_department(top_category),
        }
        return suggestions

    def _suggest_department(self, category: Optional[str]) -> Optional[str]:
        """Map category to likely responsible department."""
        dept_map = {
            'Roads & Infrastructure': 'Engineering Office',
            'Utilities': 'Public Utilities / Engineering',
            'Public Safety': 'PNP / BFP / DRRMO',
            'Environment': 'ENRO / CENRO',
            'Health & Sanitation': 'City Health Office',
            'Transportation': 'Transportation Office / TEDD',
            'Government Services': 'City Hall / Barangay Hall',
            'Education': 'DepEd / Local School Board',
        }
        return dept_map.get(category)


class InsightEngine:
    """Derives narrative insights from submitted concerns using pure Python stats.

    Runs fully offline: no API keys, no network calls. Every insight is a short
    human-readable finding backed by a number computed from the report table.
    """

    WINDOW_DAYS = 7
    BACKLOG_DAYS = 14
    HOTSPOT_DAYS = 60
    LOW_CONFIDENCE = 0.3

    def generate(self, limit: int = 6) -> Dict[str, Any]:
        from django.db.models import Count, Q
        from django.utils import timezone

        from apps.concerns.models import ConcernReport

        now = timezone.now()
        status = ConcernReport.Status
        settled_statuses = (status.RESOLVED, status.REJECTED, status.WITHDRAWN)

        reports = ConcernReport.objects.all()
        total = reports.count()
        if not total:
            return {
                'summary': (
                    'No concerns have been filed yet, so there is nothing to analyse. '
                    'Insights generate themselves automatically as soon as reports arrive.'
                ),
                'insights': [],
                'generated_at': now,
                'total_analyzed': 0,
                'needs_review': [],
            }

        settled_count = reports.filter(status__in=settled_statuses).count()
        open_count = total - settled_count
        resolved_count = reports.filter(status=status.RESOLVED).count()

        insights: List[Dict[str, Any]] = []

        # 1. Volume trend: last 7 days versus the 7 days before that.
        this_window = now - timedelta(days=self.WINDOW_DAYS)
        prev_window = now - timedelta(days=self.WINDOW_DAYS * 2)
        recent = reports.filter(submitted_at__gte=this_window).count()
        previous = reports.filter(
            submitted_at__gte=prev_window,
            submitted_at__lt=this_window,
        ).count()
        if previous:
            change = round(((recent - previous) / previous) * 100)
        elif recent:
            change = 100
        else:
            change = 0
        if change >= 25:
            insights.append({
                'icon': 'fa-arrow-trend-up',
                'tone': 'danger',
                'title': 'Report volume is surging',
                'detail': (
                    f'{recent} concern(s) were filed in the last {self.WINDOW_DAYS} days, '
                    f'a {change}% jump over the previous week ({previous}). '
                    'Consider reinforcing field teams for the next few days.'
                ),
                'metric': f'+{change}%',
            })
        elif change <= -25:
            insights.append({
                'icon': 'fa-arrow-trend-down',
                'tone': 'success',
                'title': 'Report volume is easing',
                'detail': (
                    f'Only {recent} concern(s) came in over the last {self.WINDOW_DAYS} days, '
                    f'a {abs(change)}% drop from {previous} the week before. '
                    'A good window to clear the existing backlog.'
                ),
                'metric': f'{change}%',
            })

        # 2. Dominant category.
        top_category = (
            reports.values('category__name')
            .annotate(count=Count('id'))
            .order_by('-count')
            .first()
        )
        if top_category and top_category['category__name']:
            share = round((top_category['count'] / total) * 100)
            insights.append({
                'icon': 'fa-layer-group',
                'tone': 'primary',
                'title': f"{top_category['category__name']} dominates the caseload",
                'detail': (
                    f"{top_category['count']} of {total} concerns ({share}%) fall under "
                    f"{top_category['category__name']}. A recurring theme here usually points "
                    'to a systemic service gap worth a programme-level fix.'
                ),
                'metric': f'{share}%',
            })

        # 3. Hot-spot area within the recent window.
        hotspot = (
            reports.filter(submitted_at__gte=now - timedelta(days=self.HOTSPOT_DAYS))
            .exclude(area__isnull=True)
            .values('area__name', 'area__level', 'area__parent__name')
            .annotate(count=Count('id'))
            .order_by('-count')
            .first()
        )
        if hotspot and hotspot['count'] > 1:
            place = hotspot['area__name']
            parent = hotspot['area__parent__name']
            label = f'{place}, {parent}' if parent else place
            insights.append({
                'icon': 'fa-location-dot',
                'tone': 'warning',
                'title': f'{label} is the current hot spot',
                'detail': (
                    f"{hotspot['count']} concern(s) were logged in {label} over the last "
                    f'{self.HOTSPOT_DAYS} days — the highest of any area. '
                    'A focused inspection there should resolve several reports at once.'
                ),
                'metric': f"{hotspot['count']} reports",
            })

        # 4. Ageing backlog.
        stale = reports.filter(
            submitted_at__lt=now - timedelta(days=self.BACKLOG_DAYS),
        ).exclude(status__in=settled_statuses).count()
        if stale:
            insights.append({
                'icon': 'fa-hourglass-half',
                'tone': 'danger' if stale > 3 else 'warning',
                'title': f'{stale} concern(s) are ageing past {self.BACKLOG_DAYS} days',
                'detail': (
                    f'{stale} report(s) are still unresolved more than {self.BACKLOG_DAYS} days '
                    'after submission. Ageing items are the strongest predictor of citizen '
                    'dissatisfaction — triage these first.'
                ),
                'metric': f'{stale} overdue',
            })

        # 5. Resolution rate.
        if total >= 3:
            rate = round((resolved_count / total) * 100)
            tone = 'success' if rate >= 60 else 'warning' if rate >= 30 else 'danger'
            insights.append({
                'icon': 'fa-circle-check',
                'tone': tone,
                'title': f'Resolution rate is at {rate}%',
                'detail': (
                    f'{resolved_count} of {total} concerns have been marked resolved, leaving '
                    f'{open_count} still open. '
                    + ('Performance is on track.' if rate >= 60
                       else 'Clearing the oldest open reports would lift this quickly.')
                ),
                'metric': f'{rate}%',
            })

        # 6. Duplicate clusters flagged at submission time.
        duplicate_count = reports.filter(ai_duplicate_of__isnull=False).count()
        if duplicate_count:
            cluster = (
                reports.filter(ai_duplicate_of__isnull=False)
                .values('ai_duplicate_of__subject')
                .annotate(count=Count('id'))
                .order_by('-count')
                .first()
            )
            detail = (
                f'{duplicate_count} submitted concern(s) closely match an earlier report. '
                'Merging duplicates cuts staff workload and gives citizens one clear thread '
                'to follow.'
            )
            if cluster and cluster['ai_duplicate_of__subject']:
                detail = (
                    f'{duplicate_count} submitted concern(s) closely match an earlier report. '
                    f"The busiest cluster repeats “{cluster['ai_duplicate_of__subject']}” "
                    f"({cluster['count']} follow-up report(s)). Merging duplicates cuts staff "
                    'workload and gives citizens one clear thread to follow.'
                )
            insights.append({
                'icon': 'fa-copy',
                'tone': 'azure',
                'title': 'Possible duplicate reports detected',
                'detail': detail,
                'metric': f'{duplicate_count} matches',
            })

        # 7. Data quality: reports without coordinates.
        unmapped = reports.filter(Q(latitude__isnull=True) | Q(longitude__isnull=True)).count()
        if unmapped:
            insights.append({
                'icon': 'fa-map-location-dot',
                'tone': 'secondary',
                'title': f'{unmapped} concern(s) have no map pin',
                'detail': (
                    f'{unmapped} report(s) were filed without coordinates, so they cannot be '
                    'plotted on the interactive map and may be missed during geographic '
                    'triage.'
                ),
                'metric': f'{unmapped} unmapped',
            })

        # 8. AI tagging confidence.
        low_confidence = (
            reports.filter(ai_analyzed_at__isnull=False)
            .filter(Q(ai_confidence__lte=self.LOW_CONFIDENCE) | Q(ai_confidence__isnull=True))
            .select_related('category', 'area')
            .order_by('-submitted_at')
        )
        needs_review = [
            {
                'reference': str(report.reference),
                'subject': report.subject,
                'category': report.category.name if report.category_id else 'Uncategorised',
                'suggestion': report.ai_category or 'No signal',
                'confidence': round((report.ai_confidence or 0) * 100),
            }
            for report in low_confidence[:5]
        ]
        review_count = low_confidence.count()
        if needs_review:
            insights.append({
                'icon': 'fa-triangle-exclamation',
                'tone': 'warning',
                'title': f'{review_count} report(s) need a human category check',
                'detail': (
                    'The classifier found little keyword signal in these reports, so their '
                    'suggested category is unreliable. A quick manual review keeps the '
                    'analytics trustworthy.'
                ),
                'metric': f'{review_count} low confidence',
            })

        tone_rank = {'danger': 0, 'warning': 1, 'primary': 2, 'azure': 3, 'success': 4, 'secondary': 5}
        insights.sort(key=lambda item: tone_rank.get(item['tone'], 9))

        headline = insights[0] if insights else None
        summary = (
            f'{total} concern(s) analysed, {open_count} still open and {settled_count} settled. '
            + (headline['detail'] if headline else '')
        ).strip()

        return {
            'summary': summary,
            'insights': insights[:limit],
            'generated_at': now,
            'total_analyzed': total,
            'needs_review': needs_review,
        }


# Global instances
classifier = ReportClassifier()
duplicate_detector = DuplicateDetector()
response_suggester = ResponseSuggester()
insight_engine = InsightEngine()


def classify_report(subject: str, description: str) -> List[CategoryPrediction]:
    """Convenience function to classify a report."""
    return classifier.predict(subject, description)


def find_duplicates(
    subject: str,
    description: str,
    existing_reports: List[Dict[str, Any]],
    area_id: Optional[int] = None
) -> List[DuplicateMatch]:
    """Convenience function to find duplicates."""
    return duplicate_detector.find_duplicates(subject, description, existing_reports, area_id)


def suggest_response(
    report_subject: str,
    report_description: str,
    current_status: str,
    category: Optional[str] = None
) -> Dict[str, Any]:
    """Convenience function to get response suggestions."""
    return response_suggester.suggest_response(report_subject, report_description, current_status, category)


def generate_insights(limit: int = 6) -> Dict[str, Any]:
    """Convenience function to generate the dashboard's automatic insights."""
    return insight_engine.generate(limit=limit)


def analyze_concern_report(report, save: bool = True) -> Dict[str, Any]:
    """Auto-analyse a single concern report and persist the result on the record.

    Tags the report with the classifier's best category guess and links it to a
    possible duplicate. Everything runs offline against the local database.
    """
    from django.utils import timezone

    from apps.concerns.models import ConcernReport

    predictions = classifier.predict(report.subject, report.description)
    top = predictions[0] if predictions else None
    report.ai_category = top.category if top else ''
    report.ai_subcategory = (top.subcategory or '') if top else ''
    report.ai_confidence = round(top.confidence, 4) if top else None

    candidates = ConcernReport.objects.filter(
        submitted_at__gte=report.submitted_at - timedelta(days=45),
    ).exclude(pk=report.pk)
    if report.area_id:
        candidates = candidates.filter(area_id=report.area_id)
    existing = list(
        candidates.order_by('-submitted_at').values('reference', 'subject', 'description', 'area_id')[:200]
    )

    matches = duplicate_detector.find_duplicates(
        report.subject,
        report.description,
        existing,
        area_id=report.area_id,
    )
    twin = None
    if matches:
        twin = ConcernReport.objects.filter(reference=matches[0].report_id).first()
    report.ai_duplicate_of = twin
    report.ai_duplicate_score = round(matches[0].similarity, 4) if matches else None
    report.ai_analyzed_at = timezone.now()

    if save:
        report.save(update_fields=[
            'ai_category',
            'ai_subcategory',
            'ai_confidence',
            'ai_duplicate_of',
            'ai_duplicate_score',
            'ai_analyzed_at',
        ])

    return {
        'ai_category': report.ai_category,
        'ai_subcategory': report.ai_subcategory,
        'ai_confidence': report.ai_confidence,
        'duplicate_of': str(twin.reference) if twin else None,
        'duplicate_score': report.ai_duplicate_score,
    }