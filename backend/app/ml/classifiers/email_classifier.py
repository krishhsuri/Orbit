"""
Layer 3: Pattern Classifier
Classifies emails using regex patterns with high precision.
Runs in ~5ms per email.
"""

import re
from typing import Tuple, Dict, Any

# Regex patterns for different email categories
PATTERNS = {
    'application_received': [
        r'application.*received',
        r'thank.*for.*applying',
        r'we.*received.*your.*application',
        r'application.*submitted',
        r'recieved.*application',
        r'confirmation.*application',
        r'thanks.*application',
        r'application.*was.*sent',  # LinkedIn: "your application was sent to"
        r'applied.*on',  # LinkedIn: "Applied on February 3"
        r'successfully.*submitted',
        r'successfully.*applied',
        r'your.*application.*to',  # "your application was sent to [Company]"
        r'you.*applied',  # "You applied to [Company]"
        r'thank.*you.*for.*your.*interest',
        r'we.*will.*review',
        r'reviewing.*your.*application',
        r'application.*under.*review',
        r'your.*profile.*has.*been',
        r'submitted.*your.*application',
        r'applied.*for.*the.*position',
        r'applied.*for.*this.*job',
    ],
    'application_rejected': [
        r'unfortunately',
        r'not.*moving forward',
        r'decided.*not.*proceed',
        r'other candidates',
        r'not.*selected',
        r'will not be moving forward',
        r'pursue other',
        r'thank.*but',
        r'volume of application',
        r'regret.*to.*inform',
        r'after.*careful.*consideration',
        r'not.*the.*right.*fit',
        r'position.*has.*been.*filled',
        r'decided.*to.*move.*forward.*with',
        r'won\'t.*be.*proceeding',
    ],
    'interview_invite': [
        r'interview',
        r'schedule.*call',
        r'meet.*team',
        r'next.*round',
        r'phone.*screen',
        r'video.*call',
        r'availability.*call',
        r'time.*chat',
        r'discuss.*role',
        r'would.*like.*to.*speak',
        r'set.*up.*a.*call',
        r'schedule.*a.*time',
        r'book.*a.*slot',
        r'calendly',
        r'zoom.*meeting',
        r'teams.*meeting',
        r'google.*meet',
        r'recruiter.*call',
        r'hiring.*manager',
        r'meet.*with.*you',
    ],
    'assessment_invite': [
        r'online.*assessment',
        r'coding.*challenge',
        r'hackerrank',
        r'codesignal',
        r'technical.*assessment',
        r'complete.*test',
        r'take.*test',
        r'home.*assignment',
        r'take-home',
        r'codility',
        r'leetcode',
        r'skills.*assessment',
        r'technical.*test',
        r'programming.*test',
        r'oa.*link',
        r'assessment.*link',
    ],
    'offer_letter': [
        r'offer.*letter',
        r'pleased.*to.*offer',
        r'extend.*offer',
        r'congratulations.*offer',
        r'offer.*employment',
        r'job.*offer',
        r'compensation.*package',
        r'salary.*offer',
        r'start.*date',
        r'onboarding',
        r'welcome.*to.*the.*team',
    ],
}

# Patterns that indicate email contains a list of multiple candidates
# If these match, we need to verify the user's email is mentioned
MULTI_CANDIDATE_PATTERNS = [
    # Selection/Acceptance patterns
    r'list\s+of.*(?:accepted|selected|shortlisted|eligible|volunteer)',
    r'following\s+(?:candidates|students|applicants|aspirants)',
    r'here\s+are\s+(?:the\s+)?(?:selected|accepted|shortlisted)',
    r'(?:selected|accepted|shortlisted|eligible)\s+(?:candidates|students|applicants)\s*:',
    r'congratulations\s+to\s+(?:the\s+following|all)',
    r'students\s+(?:selected|accepted)\s+for',
    r'candidates\s+moving\s+(?:forward|to\s+the\s+next)',
    # Rejection/Not selected patterns (for mass rejection emails)
    r'regret\s+to\s+inform\s+(?:the\s+)?following',
    r'(?:not\s+selected|rejected)\s+(?:candidates|students|applicants)\s*:',
    r'unfortunately.*(?:following|listed)\s+(?:candidates|students)',
    r'will\s+not\s+be\s+(?:proceeding|moving)\s+with\s*:',
    r'(?:candidates|applicants)\s+(?:not|who\s+were\s+not)\s+selected',
    # Generic list patterns
    r'attached\s+(?:is|are)\s+the\s+(?:list|names)',
    r'please\s+see\s+(?:the\s+)?(?:list|names)\s+(?:of|below)',
    r'(?:cc|bcc|copied)\s+(?:to|on)\s+(?:this|the)\s+(?:email|message)',
]

# Patterns specifically for college/placement style emails with candidate tables
# These are VERY likely to be "list of selected students" type emails
CANDIDATE_LIST_EMAIL_PATTERNS = [
    r'list\s+of\s+(?:volunteered|eligible|shortlisted)\s+(?:aspirants|students|candidates)',
    r'(?:find|see)\s+(?:below|attached)\s+the\s+names',
    r'(?:enrollment|roll\s*no|s\.?\s*no)\s+.*(?:name|email)',  # Table headers
    r'eligible\s+volunteer\s+students',
    r'kind\s+attention\s+to\s+(?:the\s+)?aspirants',
    r'hiring\s+for\s+(?:summer\s+)?internship.*batch',
    r'registration\s+link.*(?:students|candidates)',
    r'complete.*registration.*(?:recruitment|placement)',
    r'message\s+clipped',  # Gmail clips long emails - likely a big list
]



class EmailClassifier:
    """
    Layer 3: Pattern Classifier
    Classifies emails using regex patterns with high precision.
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
        # Combine subject and body for text analysis
        text = f"{email.get('subject', '')} {email.get('body_preview', '')}".lower()
        
        result = {
            'category': 'not_job_related',
            'confidence': 0.0
        }
        
        # EARLY CHECK: Detect "candidate list" emails (like Fidelity selection lists)
        # These emails list selected/eligible students - user must be IN the list
        if user_email:
            is_candidate_list_email = any(
                re.search(p, text, re.IGNORECASE) 
                for p in CANDIDATE_LIST_EMAIL_PATTERNS
            )
            
            if is_candidate_list_email:
                # Check if user's email or username is anywhere in the email
                user_name = user_email.split('@')[0].lower()
                # Also check for common name variations (remove numbers, dots)
                user_name_clean = re.sub(r'[0-9._]+', '', user_name)
                
                user_in_email = (
                    user_email.lower() in text or 
                    user_name in text or
                    (len(user_name_clean) >= 4 and user_name_clean in text)  # Min 4 chars to avoid false matches
                )
                
                if not user_in_email:
                    # This is a candidate list email and user is NOT in the visible portion
                    # Gmail clips long emails, so if not found in visible part, likely not selected
                    result['category'] = 'not_for_user'
                    result['confidence'] = 0.90
                    result['reason'] = 'candidate_list_email_user_not_found'
                    return result
        
        # 1. Check strong patterns first (high precision)
        for category, patterns in PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, text):
                    # Calculate confidence based on pattern specificity
                    confidence = 0.9 if len(pattern) > 20 else 0.8
                    
                    # Boost confidence if NLP also detected this type
                    if nlp_result.get('detected_type') == category:
                        confidence = min(0.99, confidence + 0.1)
                    
                    # IMPORTANT: For ALL job-related categories, check if this is a multi-candidate email
                    # If it lists multiple candidates, verify user's email is mentioned
                    # This prevents false positives like seeing rejection emails where user wasn't in the list
                    if user_email and category in ('interview_invite', 'application_rejected', 'application_received', 'assessment_invite', 'offer_letter'):
                        is_multi_candidate = any(
                            re.search(p, text, re.IGNORECASE) 
                            for p in MULTI_CANDIDATE_PATTERNS
                        )
                        if is_multi_candidate:
                            # Check if user's email or name is in the email
                            user_name = user_email.split('@')[0].lower()
                            user_in_email = (
                                user_email.lower() in text or 
                                user_name in text
                            )
                            if not user_in_email:
                                # User is NOT in the list - this is not for them
                                result['category'] = 'not_for_user'
                                result['confidence'] = 0.85
                                return result
                    
                    result['category'] = category
                    result['confidence'] = confidence
                    return result
        
        # 2. Fallback to NLP detection if patterns failed but NLP was confident
        if nlp_result.get('detected_type') and nlp_result.get('type_confidence', 0) > 0.7:
            result['category'] = nlp_result['detected_type']
            result['confidence'] = nlp_result['type_confidence']
            return result
        
        # 3. Check general job relatedness
        if nlp_result.get('is_likely_job_related'):
            # If it's from a recruiter/ATS but no specific category detected, 
            # it might be general correspondence or a niche status update
            result['category'] = 'general_hr'
            result['confidence'] = 0.6
            return result
        
        result['category'] = 'not_job_related'
        result['confidence'] = 0.9
        return result

