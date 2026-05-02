Implementation Plan - Solving UI and Functional Weirdness
This plan addresses the several "sudden" issues reported by the user regarding the Application Detail page and AI Agent behaviors.

Problem Analysis
Notes Layout: The "Notes" and "Email Source" components in the right sidebar feel disjointed and secondary. The user wants the email content to be more prominent and the notes to feel integrated.
Thread Redundancy: Email bodies in the timeline contain the entire thread history (quoted replies), making them extremely long and redundant.
UI Breakage (Visl Labs): Long technical strings (URLs/data) in email snippets are breaking the layout because of a lack of word-wrapping.
Action Back-dating: AI-extracted actions show the email date (e.g., Apr 28) but the "relative time" (e.g., 1h ago) is inconsistent because created_at defaults to the sync time.
Proposed Changes
[Backend]
[NEW] 
email_utils.py
Create a utility to strip quoted history from email bodies using regex patterns (On ..., ... wrote:, -----Original Message-----, etc.).
[MODIFY] 
email_sync.py
Apply strip_email_thread to the email body before saving it to PendingApplication and email_snippet.
Pass the email_date to the ActionExtractor.
[MODIFY] 
action_extractor.py
Set the created_at of the Event record to the email_timestamp if provided. This ensures the timeline and agents show the action's true occurrence date.
[Frontend]
[MODIFY] 
page.tsx
Layout Redesign:
Move "Email Source" content into a collapsible "View Full Thread" button within the timeline or as a primary component.
Expand the "Notes" section or move it to a more central location to make it feel like a workspace.
Improved Timeline: Use a specialized EmailEvent component that handles long text better and optionally hides the "thread history" if it wasn't stripped by the backend.
[MODIFY] 
page.module.css
Add word-break: break-all; and overflow-wrap: anywhere; to .timelineCardDesc, .sidePanel, and other text containers to prevent layout breakage from long strings.
Increase the prominence of the Notes section.
Verification Plan
Automated Tests
Run backend unit tests for the strip_email_thread utility with various email formats.
Manual Verification
Verify the Application Detail page on various screen sizes.
Trigger a sync for a multi-reply email thread and confirm only the latest message is shown in the timeline.
Check that the "Visl Labs" technical text now wraps correctly without breaking the UI.
Verify that Agent A actions show the correct historical date.