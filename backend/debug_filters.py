"""
Debug script to test the email filtering pipeline.
Run: python debug_filters.py
"""

import asyncio
from app.ml.filters.quick_filter import QuickFilter
from app.ml.analyzers.nlp_analyzer import NLPAnalyzer
from app.ml.classifiers.email_classifier import EmailClassifier

# Test emails - simulate real job-related emails
TEST_EMAILS = [
    {
        'id': 'test1',
        'from_address': 'jobs-noreply@linkedin.com',
        'from_name': 'LinkedIn Jobs',
        'subject': 'Your application was sent to Google',
        'snippet': 'Congratulations! Your application was sent to Google for Software Engineer position.',
        'body_preview': 'Congratulations! Your application was sent to Google for Software Engineer position.'
    },
    {
        'id': 'test2',
        'from_address': 'noreply@greenhouse.io',
        'from_name': 'Greenhouse',
        'subject': 'Thank you for applying - Software Engineer at Stripe',
        'snippet': 'We received your application for Software Engineer at Stripe.',
        'body_preview': 'We received your application for Software Engineer at Stripe. We will review and get back to you.'
    },
    {
        'id': 'test3',
        'from_address': 'recruiting@meta.com',
        'from_name': 'Meta Recruiting',
        'subject': 'Interview Invitation - Product Manager',
        'snippet': 'We would like to schedule an interview with you for the Product Manager role.',
        'body_preview': 'We would like to schedule an interview with you for the Product Manager role at Meta.'
    },
    {
        'id': 'test4',
        'from_address': 'hr@amazon.com',
        'from_name': 'Amazon HR',
        'subject': 'Online Assessment Invitation - SDE',
        'snippet': 'Please complete the HackerRank coding challenge within 7 days.',
        'body_preview': 'Please complete the HackerRank coding challenge for the SDE position within 7 days.'
    },
    {
        'id': 'test5',
        'from_address': 'careers@wellfound.com',
        'from_name': 'Wellfound',
        'subject': 'Application Update from TechStartup',
        'snippet': 'Thank you for your interest in TechStartup.',
        'body_preview': 'Thank you for your interest. Unfortunately, we have decided to pursue other candidates.'
    },
    # TEST: Multi-candidate selection list email (Fidelity-style false positive scenario)
    {
        'id': 'test6_fidelity',
        'from_address': 'careers@fidelity.com',
        'from_name': 'Fidelity Careers',
        'subject': 'Fidelity International-Hiring For Summer Internship From Batch 2027',
        'snippet': 'Please find below the names of eligible volunteer students for this drive.',
        'body_preview': '''Kind attention to the aspirants of Fidelity International-Hiring For Summer Internship From Batch 2027:
Please find below the names of eligible volunteer students for this drive.
The company has shared the registration link with the students.
It is mandatory to complete this registration to participate in the Fidelity International recruitment process.
List of Volunteered Aspirants:
S. No.	Enrollment	First Name	Last Name	Email Address
1	23102002	Dhawal	Shukla	dhawalmannu@gmail.com
2	23102003	Tanishq	Vijay	tanishq311vijay@gmail.com
3	23102009	Aayush	Bansal	aayushbansal749@gmail.com
[Message clipped] View entire message'''
    },
]

def test_pipeline():
    print("=" * 70)
    print("EMAIL DETECTION PIPELINE DEBUG")
    print("=" * 70)
    
    quick_filter = QuickFilter()
    nlp_analyzer = NLPAnalyzer()
    email_classifier = EmailClassifier()
    
    NON_JOB_STATUSES = {'not_job_related', 'not_for_user'}  # Match gmail.py
    
    for i, email in enumerate(TEST_EMAILS, 1):
        print(f"\n{'='*70}")
        print(f"TEST EMAIL {i}: {email['subject'][:50]}")
        print(f"From: {email['from_address']}")
        print(f"{'='*70}")
        
        # Layer 1: Quick Filter
        passed_quick_filter = quick_filter.initial_filter(
            email['from_address'], 
            email['subject']
        )
        print(f"\n[Layer 1] QuickFilter: {'✅ PASSED' if passed_quick_filter else '❌ BLOCKED'}")
        
        if not passed_quick_filter:
            print("   ⚠️  Email was blocked by QuickFilter - won't be processed further")
            continue
        
        # Layer 2: NLP Analysis
        nlp_result = nlp_analyzer.analyze_email(email)
        print(f"\n[Layer 2] NLP Analyzer:")
        print(f"   - keyword_score: {nlp_result.get('keyword_score', 0)}")
        print(f"   - detected_type: {nlp_result.get('detected_type', 'None')}")
        print(f"   - type_confidence: {nlp_result.get('type_confidence', 0):.2f}")
        print(f"   - is_likely_job_related: {nlp_result.get('is_likely_job_related', False)}")
        print(f"   - company: {nlp_result.get('company', 'None')}")
        print(f"   - organizations: {nlp_result.get('entities', {}).get('organizations', [])}")
        print(f"   - sender_signals: {nlp_result.get('sender_signals', {})}")
        
        # Layer 3: Email Classifier
        # Pass user_email to test multi-candidate detection
        test_user_email = "testuser@gmail.com"  # User NOT in the Fidelity rejection list
        classification = email_classifier.classify(email, nlp_result, user_email=test_user_email)
        print(f"\n[Layer 3] Email Classifier (user_email={test_user_email}):")
        print(f"   - category: {classification.get('category', 'unknown')}")
        print(f"   - confidence: {classification.get('confidence', 0):.2f}")
        
        # Final Check: Would this be filtered out?
        status = classification.get('category', 'unknown')
        would_be_filtered = status in NON_JOB_STATUSES
        
        print(f"\n[RESULT]")
        if would_be_filtered:
            print(f"   ❌ FILTERED OUT - Status '{status}' is in NON_JOB_STATUSES")
        else:
            print(f"   ✅ WOULD BE SAVED - Status: {status} (confidence: {classification.get('confidence', 0):.2f})")

if __name__ == "__main__":
    test_pipeline()
