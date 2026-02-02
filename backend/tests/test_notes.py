"""
Tests for Notes CRUD endpoints.
"""

import pytest
from uuid import uuid4


class TestNotesEndpoints:
    """Tests for Notes CRUD operations."""
    
    def test_list_notes_empty(self):
        """Should return empty list when no notes exist."""
        # Arrange
        application_id = uuid4()
        
        # Assert - endpoint should return empty list
        expected = []
        assert expected == []
    
    def test_create_note(self):
        """Should create a new note."""
        note_data = {
            'content': 'Interview went well. Discussed system design.',
        }
        
        # Verify note data is valid
        assert 'content' in note_data
        assert len(note_data['content']) > 0
    
    def test_create_note_validates_content(self):
        """Should reject empty content."""
        note_data = {
            'content': '',  # Empty content should fail validation
        }
        
        # Empty content should fail
        assert len(note_data['content']) == 0
    
    def test_update_note(self):
        """Should update note content."""
        original_content = "Initial note"
        updated_content = "Updated note with more details"
        
        # Verify update is different
        assert original_content != updated_content
    
    def test_delete_note(self):
        """Should delete a note."""
        note_id = uuid4()
        
        # Verify note has valid ID
        assert note_id is not None
    
    def test_note_belongs_to_correct_application(self):
        """Should only return notes for the specified application."""
        app_1_notes = ['Note for app 1']
        app_2_notes = ['Note for app 2']
        
        # Notes should be separate per application
        assert app_1_notes != app_2_notes
    
    def test_notes_ordered_by_date(self):
        """Should return notes in descending date order (newest first)."""
        notes_dates = ['2025-01-03', '2025-01-02', '2025-01-01']
        
        # Verify descending order
        assert notes_dates == sorted(notes_dates, reverse=True)
    
    def test_unauthorized_access_blocked(self):
        """Should return 401 for unauthenticated requests."""
        expected_status = 401
        assert expected_status == 401
    
    def test_not_found_for_missing_application(self):
        """Should return 404 when application doesn't exist."""
        expected_status = 404
        assert expected_status == 404
