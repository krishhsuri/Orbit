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
    ],
    'offer_letter': [
        r'offer.*letter',
        r'pleased.*to.*offer',
        r'extend.*offer',
        r'congratulations.*offer',
        r'offer.*employment',
    ],
}



class EmailClassifier:
    """
    Layer 3: Pattern Classifier
    Classifies emails using regex patterns with high precision.
    """
    
    def classify(self, email: dict, nlp_result: dict) -> Dict[str, Any]:
        """
        Classify email into category based on patterns and NLP signals.
        
        Args:
            email: Raw email dict
            nlp_result: Result from Layer 2 NLP analyzer
            
        Returns:
            Dict with category and confidence
        """
        # Combine subject and body for text analysis
        text = f"{email.get('subject', '')} {email.get('body_preview', '')}".lower()
        
        result = {
            'category': 'not_job_related',
            'confidence': 0.0
        }
        
        # 1. Check strong patterns first (high precision)
        for category, patterns in PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, text):
                    # Calculate confidence based on pattern specificity
                    confidence = 0.9 if len(pattern) > 20 else 0.8
                    
                    # Boost confidence if NLP also detected this type
                    if nlp_result.get('detected_type') == category:
                        confidence = min(0.99, confidence + 0.1)
                    
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
