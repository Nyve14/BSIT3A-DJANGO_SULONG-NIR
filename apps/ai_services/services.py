import re
import json
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


# Global instances
classifier = ReportClassifier()
duplicate_detector = DuplicateDetector()
response_suggester = ResponseSuggester()


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