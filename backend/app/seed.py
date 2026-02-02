"""
Comprehensive Seed Script for Development
Creates demo user with realistic sample data.
Run: python -m app.seed
"""

import asyncio
import random
from datetime import date, datetime, timedelta
from uuid import UUID, uuid4

from app.database import async_session_maker
from app.models import User, Application, Tag, Event, Note


DEMO_USER_ID = UUID("00000000-0000-0000-0000-000000000001")

# Sample data pools
COMPANIES = [
    ("Google", "google.com"),
    ("Meta", "meta.com"),
    ("Amazon", "amazon.com"),
    ("Apple", "apple.com"),
    ("Microsoft", "microsoft.com"),
    ("Netflix", "netflix.com"),
    ("Stripe", "stripe.com"),
    ("Airbnb", "airbnb.com"),
    ("Uber", "uber.com"),
    ("Spotify", "spotify.com"),
    ("Slack", "slack.com"),
    ("Dropbox", "dropbox.com"),
    ("Coinbase", "coinbase.com"),
    ("Figma", "figma.com"),
    ("Notion", "notion.so"),
    ("Discord", "discord.com"),
    ("Twitch", "twitch.tv"),
    ("Shopify", "shopify.com"),
    ("Square", "squareup.com"),
    ("Robinhood", "robinhood.com"),
    ("Plaid", "plaid.com"),
    ("Datadog", "datadoghq.com"),
    ("MongoDB", "mongodb.com"),
    ("Snowflake", "snowflake.com"),
    ("Databricks", "databricks.com"),
]

ROLES = [
    "Software Engineer",
    "Software Engineer Intern",
    "Frontend Engineer",
    "Backend Engineer",
    "Full Stack Engineer",
    "Machine Learning Engineer",
    "Data Engineer",
    "DevOps Engineer",
    "Site Reliability Engineer",
    "Product Manager",
    "Product Manager Intern",
    "Technical Program Manager",
    "Solutions Architect",
    "Data Scientist",
    "Security Engineer",
]

STATUSES = ["applied", "screening", "oa", "interview", "offer", "accepted", "rejected", "ghosted", "withdrawn"]
STATUS_WEIGHTS = [25, 10, 8, 12, 5, 2, 20, 15, 3]  # Realistic distribution

SOURCES = ["linkedin", "direct", "referral", "indeed", "glassdoor", "company_site", "handshake"]
SOURCE_WEIGHTS = [30, 25, 15, 10, 8, 8, 4]

LOCATIONS = [
    "San Francisco, CA",
    "New York, NY",
    "Seattle, WA",
    "Austin, TX",
    "Remote",
    "Hybrid - NYC",
    "Hybrid - SF",
    "Boston, MA",
    "Los Angeles, CA",
    "Chicago, IL",
]

TAGS = [
    ("Python", "#3776AB"),
    ("JavaScript", "#F7DF1E"),
    ("TypeScript", "#3178C6"),
    ("React", "#61DAFB"),
    ("Node.js", "#339933"),
    ("AWS", "#FF9900"),
    ("Kubernetes", "#326CE5"),
    ("Machine Learning", "#FF6F00"),
    ("Startup", "#00D4AA"),
    ("FAANG", "#4285F4"),
    ("Remote", "#10B981"),
    ("Internship", "#8B5CF6"),
]

EVENT_TYPES = [
    ("created", "Application created"),
    ("status_change", "Status updated"),
    ("interview_scheduled", "Interview scheduled"),
    ("note_added", "Note added"),
    ("followup_sent", "Follow-up email sent"),
]

SAMPLE_NOTES = [
    "Had a great call with the recruiter. Team seems friendly.",
    "Technical phone screen went well. Discussed system design.",
    "Need to prepare for behavioral questions.",
    "Sent follow-up email after no response for a week.",
    "Completed online assessment - mostly LC medium problems.",
    "Virtual onsite scheduled for next Tuesday.",
    "Received offer! Need to negotiate salary.",
    "Declined due to better opportunity.",
    "Referral from a friend who works there.",
    "Company has great WLB according to Glassdoor.",
]


async def seed_all():
    """Create comprehensive sample data."""
    async with async_session_maker() as session:
        try:
            from sqlalchemy import select
            
            # Check if demo user exists
            result = await session.execute(
                select(User).where(User.id == DEMO_USER_ID)
            )
            user = result.scalar_one_or_none()
            
            if not user:
                user = User(
                    id=DEMO_USER_ID,
                    email="demo@orbit.dev",
                    name="Demo User",
                    preferences={"weekly_goal": 15, "theme": "dark"},
                )
                session.add(user)
                await session.flush()
                print("✓ Created demo user: demo@orbit.dev")
            else:
                print("✓ Demo user already exists")
            
            # Check if applications exist
            result = await session.execute(
                select(Application).where(Application.user_id == DEMO_USER_ID).limit(1)
            )
            if result.scalar_one_or_none():
                print("✓ Sample applications already exist, skipping...")
                return
            
            # Create tags
            created_tags = []
            for tag_name, color in TAGS:
                tag = Tag(
                    id=uuid4(),
                    user_id=DEMO_USER_ID,
                    name=tag_name,
                    color=color,
                )
                session.add(tag)
                created_tags.append(tag)
            await session.flush()
            print(f"✓ Created {len(created_tags)} tags")
            
            # Create applications
            created_apps = []
            today = date.today()
            
            for i, (company, domain) in enumerate(COMPANIES):
                # Random application date in last 60 days
                days_ago = random.randint(1, 60)
                applied_date = today - timedelta(days=days_ago)
                
                # Select status with weighted probability
                status = random.choices(STATUSES, weights=STATUS_WEIGHTS)[0]
                
                # Select source
                source = random.choices(SOURCES, weights=SOURCE_WEIGHTS)[0]
                
                # Random role
                role = random.choice(ROLES)
                
                # Random location
                location = random.choice(LOCATIONS)
                
                # Salary range (vary by company prestige)
                base_salary = random.randint(80, 200) * 1000
                salary_max = base_salary + random.randint(20, 50) * 1000
                
                app = Application(
                    id=uuid4(),
                    user_id=DEMO_USER_ID,
                    company_name=company,
                    role_title=role,
                    status=status,
                    applied_date=applied_date,
                    job_url=f"https://careers.{domain}/jobs/{random.randint(10000, 99999)}",
                    salary_min=base_salary,
                    salary_max=salary_max,
                    salary_currency="USD",
                    location=location,
                    remote_type="remote" if "Remote" in location else "hybrid" if "Hybrid" in location else "onsite",
                    source=source,
                    priority=random.choice(["low", "medium", "high"]),
                    status_updated_at=datetime.utcnow() - timedelta(days=random.randint(0, days_ago)),
                )
                
                # Add 1-3 random tags
                num_tags = random.randint(1, 3)
                app.tags = random.sample(created_tags, min(num_tags, len(created_tags)))
                
                session.add(app)
                created_apps.append(app)
            
            await session.flush()
            print(f"✓ Created {len(created_apps)} applications")
            
            # Create events for each application
            event_count = 0
            for app in created_apps:
                # Always create "created" event
                event = Event(
                    id=uuid4(),
                    application_id=app.id,
                    event_type="created",
                    title="Application created",
                    data={"status": "applied"},
                    created_at=datetime.combine(app.applied_date, datetime.min.time()),
                )
                session.add(event)
                event_count += 1
                
                # Add 1-3 random events if not just applied
                if app.status != "applied":
                    num_events = random.randint(1, 3)
                    for j in range(num_events):
                        event_type, title = random.choice(EVENT_TYPES[1:])
                        event = Event(
                            id=uuid4(),
                            application_id=app.id,
                            event_type=event_type,
                            title=title,
                            data={"auto_generated": True},
                            created_at=datetime.utcnow() - timedelta(days=random.randint(0, 30)),
                        )
                        session.add(event)
                        event_count += 1
            
            await session.flush()
            print(f"✓ Created {event_count} events")
            
            # Create notes for some applications
            note_count = 0
            for app in random.sample(created_apps, min(15, len(created_apps))):
                num_notes = random.randint(1, 2)
                for _ in range(num_notes):
                    note = Note(
                        id=uuid4(),
                        application_id=app.id,
                        content=random.choice(SAMPLE_NOTES),
                        created_at=datetime.utcnow() - timedelta(days=random.randint(0, 30)),
                    )
                    session.add(note)
                    note_count += 1
            
            await session.commit()
            print(f"✓ Created {note_count} notes")
            print("\n✅ Seed complete!")
            print(f"   - 1 demo user")
            print(f"   - {len(created_tags)} tags")
            print(f"   - {len(created_apps)} applications")
            print(f"   - {event_count} events")
            print(f"   - {note_count} notes")
            
        except Exception as e:
            print(f"✗ Error seeding data: {e}")
            await session.rollback()
            raise


async def clear_demo_data():
    """Clear all demo user data (for re-seeding)."""
    async with async_session_maker() as session:
        try:
            from sqlalchemy import delete
            
            # Delete in order of dependencies
            await session.execute(
                delete(Note).where(
                    Note.application_id.in_(
                        select(Application.id).where(Application.user_id == DEMO_USER_ID)
                    )
                )
            )
            await session.execute(
                delete(Event).where(
                    Event.application_id.in_(
                        select(Application.id).where(Application.user_id == DEMO_USER_ID)
                    )
                )
            )
            await session.execute(
                delete(Application).where(Application.user_id == DEMO_USER_ID)
            )
            await session.execute(
                delete(Tag).where(Tag.user_id == DEMO_USER_ID)
            )
            
            await session.commit()
            print("✓ Cleared demo user data")
            
        except Exception as e:
            print(f"✗ Error clearing data: {e}")
            await session.rollback()
            raise


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--clear":
        asyncio.run(clear_demo_data())
    else:
        asyncio.run(seed_all())
