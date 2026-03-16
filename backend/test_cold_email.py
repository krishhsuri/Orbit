import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'app')))

from app.ml.classifiers.cold_email_detector import ColdEmailDetector

def test_detector():
    detector = ColdEmailDetector()
    
    cases = [
        {"subject": "Application for Software Engineer at Google", "to_address": "hr@google.com"},
        {"subject": "application : Frontend Developer - Meta", "to_address": "careers@meta.com"},
        {"subject": "Interest in the Backend Engineer Role", "to_address": "founder@startup.io"},
        {"subject": "Re: Application for Software Engineer", "to_address": "recruiter@company.com"},
        {"subject": "Fwd: My CV", "to_address": "friend@gmail.com"},
        {"subject": "Just saying hi", "to_address": "someone@example.com"},
        {"subject": "Applying for Data Scientist intern", "to_address": "hiring@openai.com"},
    ]
    
    for case in cases:
        res = detector.detect(case)
        print(f"Subj: '{case['subject']}' | To: {case['to_address']}")
        print(f"  Result: {res}")
        print("-" * 50)

if __name__ == "__main__":
    test_detector()
