"""
Layer 3: Pattern Classifier
Classifies emails using regex patterns with high precision.
Fix #7: Scores ALL categories and returns the BEST match (no longer returns on first match).
Fix #8: Tightened overly broad patterns, especially 'interview'.
Runs in ~5ms per email.
"""

import re
from typing import Tuple, Dict, Any, List

# Regex patterns for different email categories.
# Patterns are ordered from most-specific (high confidence) to least-specific (low confidence).
# Each pattern tuple is (regex, confidence_weight) — higher = more specific.
PATTERNS: Dict[str, List[Tuple[str, float]]] = {
    'application_received': [
        (r'thank.*you.*for.*applying', 0.95),
        (r'we.*received.*your.*application', 0.95),
        (r'successfully.*submitted', 0.90),
        (r'successfully.*applied', 0.90),
        (r'application.*submitted', 0.90),
        (r'application.*received', 0.90),
        (r'submitted.*your.*application', 0.88),
        (r'applied.*for.*the.*position', 0.88),
        (r'applied.*for.*this.*job', 0.88),
        (r'your.*application.*to', 0.85),
        (r'application.*was.*sent', 0.85),
        (r'you.*applied', 0.80),
        (r'thank.*you.*for.*your.*interest', 0.80),
        (r'reviewing.*your.*application', 0.80),
        (r'application.*under.*review', 0.80),
        (r'we.*will.*review', 0.75),
        (r'recieved.*application', 0.75),
        (r'confirmation.*application', 0.75),
        (r'thanks.*application', 0.75),
        (r'applied.*on', 0.70),
        (r'your.*profile.*has.*been', 0.65),
    ],
    'application_rejected': [
        (r'regret.*to.*inform', 0.95),
        (r'not.*moving.*forward.*with.*your', 0.95),
        (r'decided.*not.*to.*proceed.*with.*you', 0.95),
        (r'will\s+not\s+be\s+moving\s+forward', 0.92),
        (r'not.*the.*right.*fit', 0.92),
        (r'position.*has.*been.*filled', 0.90),
        (r'won\'t.*be.*proceeding', 0.90),
        (r'after.*careful.*consideration.*not', 0.90),
        (r'decided.*to.*move.*forward\s+with\s+(?:other|another)', 0.88),
        (r'not.*selected.*for.*this', 0.88),
        (r'pursue.*other.*candidates', 0.85),
        (r'unfortunately.*we.*(?:will|won|can).*not', 0.85),
        (r'thank.*you.*but', 0.75),
        (r'high.*volume.*of.*application', 0.75),
    ],
    'interview_invite': [
        # Fix #8: 'interview' alone is too broad — require action/context words
        (r'schedule.*(?:an?\s+)?interview', 0.95),
        (r'invite.*(?:you.*)?(?:for|to).*interview', 0.95),
        (r'interview.*(?:invite|invitation|request)', 0.95),
        (r'phone\s+screen(?:\s+with)?', 0.92),
        (r'technical\s+interview', 0.92),
        (r'next\s+round\s+(?:of\s+)?interview', 0.90),
        (r'video\s+interview', 0.90),
        (r'onsite\s+interview', 0.90),
        (r'would.*like.*to.*speak.*with\s+you', 0.88),
        (r'set.*up.*(?:a\s+)?(?:call|interview|meeting)', 0.85),
        (r'schedule.*a.*time.*(?:to\s+)?(?:speak|chat|talk)', 0.85),
        (r'share.*your.*availability', 0.83),
        (r'book.*(?:a\s+)?(?:slot|time)', 0.82),
        (r'calendly.*(?:link|schedule)', 0.82),
        (r'zoom.*(?:meeting|call)\s+(?:for|to)', 0.82),
        (r'recruiter.*call', 0.80),
        (r'meet.*(?:with\s+)?(?:our\s+)?(?:team|hiring\s+manager)', 0.80),
        (r'google\s+meet.*(?:link|join)', 0.78),
        (r'teams\s+meeting.*(?:link|join)', 0.78),
    ],
    'assessment_invite': [
        (r'online.*assessment', 0.95),
        (r'coding.*challenge', 0.95),
        (r'hackerrank.*(?:test|assessment|link)', 0.95),
        (r'codesignal.*(?:test|assessment|link)', 0.95),
        (r'technical.*assessment', 0.92),
        (r'take-home.*(?:assignment|test|project)', 0.92),
        (r'home.*assignment', 0.90),
        (r'codility.*(?:test|assessment)', 0.90),
        (r'complete.*(?:the\s+)?(?:test|assessment)', 0.88),
        (r'take.*(?:the\s+)?(?:test|assessment)', 0.85),
        (r'skills.*assessment', 0.85),
        (r'technical.*test', 0.85),
        (r'programming.*test', 0.85),
        (r'assessment.*link', 0.82),
        (r'oa.*link', 0.80),
        (r'leetcode.*(?:problem|challenge)', 0.75),
    ],
    'offer_letter': [
        (r'pleased.*to.*offer\s+you', 0.98),
        (r'offer.*of.*employment', 0.96),
        (r'job\s+offer.*(?:letter|attached)', 0.95),
        (r'extend.*(?:an?\s+)?offer', 0.95),
        (r'congratulations.*we.*(?:would|are).*offer', 0.95),
        (r'compensation.*package.*(?:include|detail|attach)', 0.92),
        (r'salary.*offer', 0.90),
        (r'offer\s+letter', 0.90),
        (r'welcome.*to.*(?:the\s+)?team', 0.88),
        (r'start.*date.*(?:would|will|is)', 0.85),
        (r'onboarding.*(?:process|information|date)', 0.82),
    ],
}

# Patterns that indicate email contains a list of multiple candidates
MULTI_CANDIDATE_PATTERNS = [
    r'list\s+of.*(?:accepted|selected|shortlisted|eligible|volunteer)',
    r'following\s+(?:candidates|students|applicants|aspirants)',
    r'here\s+are\s+(?:the\s+)?(?:selected|accepted|shortlisted)',
    r'(?:selected|accepted|shortlisted|eligible)\s+(?:candidates|students|applicants)\s*:',
    r'congratulations\s+to\s+(?:the\s+following|all)',
    r'students\s+(?:selected|accepted)\s+for',
    r'candidates\s+moving\s+(?:forward|to\s+the\s+next)',
    r'regret\s+to\s+inform\s+(?:the\s+)?following',
    r'(?:not\s+selected|rejected)\s+(?:candidates|students|applicants)\s*:',
    r'unfortunately.*(?:following|listed)\s+(?:candidates|students)',
    r'will\s+not\s+be\s+(?:proceeding|moving)\s+with\s*:',
    r'(?:candidates|applicants)\s+(?:not|who\s+were\s+not)\s+selected',
    r'attached\s+(?:is|are)\s+the\s+(?:list|names)',
    r'please\s+see\s+(?:the\s+)?(?:list|names)\s+(?:of|below)',
    r'(?:cc|bcc|copied)\s+(?:to|on)\s+(?:this|the)\s+(?:email|message)',
]

CANDIDATE_LIST_EMAIL_PATTERNS = [
    r'list\s+of\s+(?:volunteered|eligible|shortlisted)\s+(?:aspirants|students|candidates)',
    r'(?:find|see)\s+(?:below|attached)\s+the\s+names',
    r'(?:enrollment|roll\s*no|s\.?\s*no)\s+.*(?:name|email)',
    r'eligible\s+volunteer\s+students',
    r'kind\s+attention\s+to\s+(?:the\s+)?aspirants',
    r'hiring\s+for\s+(?:summer\s+)?internship.*batch',
    r'registration\s+link.*(?:students|candidates)',
    r'complete.*registration.*(?:recruitment|placement)',
    r'message\s+clipped',
]


class EmailClassifier:
    """
    Layer 3: Pattern Classifier
    Fix #7: Scores ALL categories and picks the winner — no longer returns on first match.
    Fix #8: Tighter, more specific regex patterns.
    """

    def classify(self, email: dict, nlp_result: dict, user_email: str = None) -> Dict[str, Any]:
        """
        Classify email into category based on patterns and NLP signals.

        Args:
            email: Raw email dict
            nlp_result: Result from Layer 2 NLP analyzer
            user_email: Optional user's email to verify multi-candidate emails

        Returns:
            Dict with category and confidence
        """
        text = f"{email.get('subject', '')} {email.get('body_preview', '')}".lower()

        result = {
            'category': 'not_job_related',
            'confidence': 0.0
        }

        # EARLY CHECK: Detect "candidate list" emails
        if user_email:
            is_candidate_list_email = any(
                re.search(p, text, re.IGNORECASE)
                for p in CANDIDATE_LIST_EMAIL_PATTERNS
            )

            if is_candidate_list_email:
                user_name = user_email.split('@')[0].lower()
                user_name_clean = re.sub(r'[0-9._]+', '', user_name)

                user_in_email = (
                    user_email.lower() in text or
                    user_name in text or
                    (len(user_name_clean) >= 4 and user_name_clean in text)
                )

                if not user_in_email:
                    result['category'] = 'not_for_user'
                    result['confidence'] = 0.90
                    result['reason'] = 'candidate_list_email_user_not_found'
                    return result

        # Fix #7: Score ALL categories and pick the best match
        # Instead of returning on first match, collect all hits and take the winner
        category_scores: Dict[str, float] = {}

        for category, pattern_list in PATTERNS.items():
            for pattern, weight in pattern_list:
                if re.search(pattern, text, re.IGNORECASE):
                    current_best = category_scores.get(category, 0.0)
                    if weight > current_best:
                        category_scores[category] = weight
                    break  # Only use the first (most specific) matching pattern per category

        if category_scores:
            # Pick the category with the highest confidence score
            best_category = max(category_scores, key=category_scores.__getitem__)
            best_confidence = category_scores[best_category]

            # Boost confidence slightly if NLP also independently detected the same type
            nlp_type = nlp_result.get('detected_type', '')
            if nlp_type and nlp_type in best_category:
                best_confidence = min(0.99, best_confidence + 0.04)

            # Multi-candidate email check for matched job-related categories
            if user_email and best_category in (
                'interview_invite', 'application_rejected', 'application_received',
                'assessment_invite', 'offer_letter'
            ):
                is_multi_candidate = any(
                    re.search(p, text, re.IGNORECASE)
                    for p in MULTI_CANDIDATE_PATTERNS
                )
                if is_multi_candidate:
                    user_name = user_email.split('@')[0].lower()
                    user_in_email = (
                        user_email.lower() in text or
                        user_name in text
                    )
                    if not user_in_email:
                        result['category'] = 'not_for_user'
                        result['confidence'] = 0.85
                        return result

            result['category'] = best_category
            result['confidence'] = best_confidence
            return result

        # 2. Fallback to NLP detection if no patterns matched but NLP was confident
        if nlp_result.get('detected_type') and nlp_result.get('type_confidence', 0) > 0.7:
            result['category'] = nlp_result['detected_type']
            result['confidence'] = nlp_result['type_confidence']
            return result

        # 3. Check general job relatedness
        if nlp_result.get('is_likely_job_related'):
            result['category'] = 'general_hr'
            result['confidence'] = 0.6
            return result

        result['category'] = 'not_job_related'
        result['confidence'] = 0.9
        return result
