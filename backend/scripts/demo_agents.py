import asyncio
import sys
import os
from uuid import UUID, uuid4
from datetime import datetime, timedelta

# Add parent directory to sys.path to import app modules
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.services.action_extractor import ActionExtractor
from app.services.follow_up_agent import FollowUpAgent
from app.models.application import Application
from app.models.event import Event
from app.database import async_session_maker, Base, engine

# Mock Groq responses for demo if API key is missing
async def mock_extract_actions(*args, **kwargs):
    return {
        "is_job_related": True,
        "actions": [
            {
                "action_type": "online_assessment",
                "deadline": (datetime.now() + timedelta(days=3)).isoformat(),
                "urgency": "high",
                "confidence": 0.95,
                "source_text": "Please complete the technical assessment by Thursday.",
                "reasoning": "Explicit request for online assessment with a deadline."
            }
        ]
    }

async def mock_generate_draft(*args, **kwargs):
    return "Dear Hiring Team,\n\nI hope you're having a great week. I'm following up on my application for the Software Engineer role at Acme Corp. I'm still very interested in the position and would appreciate an update on the status of my application.\n\nBest regards,\nCandidate"

async def run_demo():
    print("=== Orbit AI Agents Demo ===")
    
    # 1. Setup Mock Data
    app_id = uuid4()
    user_id = uuid4()
    
    print(f"\n[Step 1] Initializing Demo Application: Acme Corp - Software Engineer")
    
    # We'll use a real DB session for the demo if possible, but let's just show the logic
    # To keep it safe and isolated, we'll just instantiate the agents and mock the LLM part if needed.
    
    extractor = ActionExtractor()
    follow_up_agent = FollowUpAgent()
    
    # Override LLM calls for the demo to ensure it works without a real key
    if not os.getenv("GROQ_API_KEY") or os.getenv("GROQ_API_KEY") == "your-groq-api-key":
        print("Note: GROQ_API_KEY not found. Using mock LLM responses.")
        extractor.llm.extract_actions_from_email = mock_extract_actions
        follow_up_agent.llm.generate_follow_up_draft = mock_generate_draft
    
    # 2. Part A: Action Extraction
    print("\n[Step 2] Agent A: Extracting Actions from Email...")
    email_body = "Hi there, thank you for your interest in Acme Corp. We'd like to invite you to take a technical assessment. Please complete it by Thursday. Good luck!"
    
    # Normally this would save to DB, but for demo we just show the output
    actions = await extractor.llm.extract_actions_from_email(
        subject="Technical Assessment Invitation",
        body=email_body
    )
    
    print(f"Extracted Actions: {actions}")
    
    # 3. Part B: Follow-up Decision
    print("\n[Step 3] Agent B: Evaluating Follow-up for a Dormant Application...")
    
    # Mocking the evaluation result since we don't want to mess with a real DB here
    # In reality, evaluate_application would query the DB.
    
    # Case 1: Too soon
    print("\nCase 1: Application updated 2 days ago")
    print("Decision: should_follow_up=False, reason='Only 2 days since last interaction (threshold: 7).'")
    
    # Case 2: Dormant for 10 days
    print("\nCase 2: Application dormant for 10 days")
    draft = await follow_up_agent.llm.generate_follow_up_draft(
        company="Acme Corp",
        role="Software Engineer",
        last_interaction_days=10
    )
    
    print(f"Decision: should_follow_up=True")
    print(f"Draft Generated:\n---\n{draft}\n---")

    print("\n=== Demo Completed Successfully ===")

if __name__ == "__main__":
    asyncio.run(run_demo())
