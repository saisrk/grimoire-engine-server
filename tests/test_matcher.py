"""
Tests for Matcher Service.

Tests the spell matching functionality including error extraction,
candidate querying, similarity computation, and ranking.
"""

import pytest
from sqlalchemy import select

from app.models.spell import Spell
from app.services.matcher import MatcherService


@pytest.mark.asyncio
class TestMatcherService:
    """Test suite for MatcherService."""
    
    async def test_match_spells_with_matching_error_type(self, test_db):
        """Test matching spells with a matching error type."""
        # Create test spells
        spell1 = Spell(
            title="Fix undefined variable",
            description="Handle undefined variable access in JavaScript",
            error_type="TypeError",
            error_pattern="undefined.*variable",
            solution_code="if (variable !== undefined) { ... }",
            tags="javascript,undefined"
        )
        spell2 = Spell(
            title="Fix null pointer",
            description="Handle null pointer exceptions",
            error_type="NullPointerException",
            error_pattern="null.*pointer",
            solution_code="if (obj != null) { ... }",
            tags="java,null"
        )
        spell3 = Spell(
            title="Fix type mismatch",
            description="Handle type mismatch errors with proper casting",
            error_type="TypeError",
            error_pattern="type.*mismatch",
            solution_code="const value = String(input);",
            tags="javascript,types"
        )
        
        test_db.add_all([spell1, spell2, spell3])
        await test_db.commit()
        
        # Create matcher service
        matcher = MatcherService(test_db)
        
        # Test error payload
        error_payload = {
            "error_type": "TypeError",
            "message": "Cannot access property of undefined variable",
            "context": "const value = myVariable.property;"
        }
        
        # Match spells
        result = await matcher.match_spells(error_payload)
        
        # Should return spell IDs, with TypeError spells ranked higher
        assert isinstance(result, list)
        assert len(result) > 0
        
        # Verify only TypeError spells are returned (spell1 and spell3)
        assert spell1.id in result
        assert spell3.id in result
        assert spell2.id not in result
    
    async def test_match_spells_returns_empty_for_no_matches(self, test_db):
        """Test that match_spells returns empty list when no spells match."""
        # Create a spell with different error type
        spell = Spell(
            title="Fix syntax error",
            description="Handle syntax errors",
            error_type="SyntaxError",
            error_pattern="syntax.*error",
            solution_code="// Fix syntax",
            tags="syntax"
        )
        test_db.add(spell)
        await test_db.commit()
        
        # Create matcher service
        matcher = MatcherService(test_db)
        
        # Test error payload with different error type
        error_payload = {
            "error_type": "ImportError",
            "message": "Cannot import module",
            "context": "import nonexistent"
        }
        
        # Match spells
        result = await matcher.match_spells(error_payload)
        
        # Should return empty list
        assert result == []
    
    async def test_match_spells_ranks_by_similarity(self, test_db):
        """Test that spells are ranked by similarity score."""
        # Create spells with varying similarity to test error
        spell1 = Spell(
            title="Exact match",
            description="undefined variable property access error",
            error_type="TypeError",
            error_pattern="undefined.*property",
            solution_code="check undefined",
            tags="undefined"
        )
        spell2 = Spell(
            title="Partial match",
            description="type error handling",
            error_type="TypeError",
            error_pattern="type.*error",
            solution_code="handle types",
            tags="types"
        )
        
        test_db.add_all([spell1, spell2])
        await test_db.commit()
        
        # Create matcher service
        matcher = MatcherService(test_db)
        
        # Test error payload that matches spell1 better
        error_payload = {
            "error_type": "TypeError",
            "message": "undefined property access",
            "context": "variable.property"
        }
        
        # Match spells
        result = await matcher.match_spells(error_payload)
        
        # Should return both spells, with spell1 ranked higher
        assert len(result) == 2
        assert result[0] == spell1.id  # spell1 should be first (better match)
    
    async def test_extract_error_characteristics(self, test_db):
        """Test error characteristic extraction."""
        matcher = MatcherService(test_db)
        
        error_payload = {
            "error_type": "TypeError",
            "message": "Cannot read property 'length' of undefined",
            "context": "const len = myArray.length;",
            "stack_trace": "at line 42"
        }
        
        characteristics = matcher._extract_error_characteristics(error_payload)
        
        assert characteristics["error_type"] == "typeerror"
        assert "cannot" in characteristics["message"]
        assert "length" in characteristics["message"]
        assert "myarray" in characteristics["context"]
    
    async def test_extract_error_characteristics_with_missing_fields(self, test_db):
        """Test error extraction with missing fields."""
        matcher = MatcherService(test_db)
        
        error_payload = {
            "error_type": "TypeError"
            # Missing message and context
        }
        
        characteristics = matcher._extract_error_characteristics(error_payload)
        
        assert characteristics["error_type"] == "typeerror"
        assert characteristics["message"] == ""
        assert characteristics["context"] == ""
    
    async def test_query_candidate_spells(self, test_db):
        """Test querying candidate spells by error type."""
        # Create spells with different error types
        spell1 = Spell(
            title="Type error fix",
            description="Fix type errors",
            error_type="TypeError",
            error_pattern="type.*error",
            solution_code="fix types",
            tags="types"
        )
        spell2 = Spell(
            title="Syntax error fix",
            description="Fix syntax errors",
            error_type="SyntaxError",
            error_pattern="syntax.*error",
            solution_code="fix syntax",
            tags="syntax"
        )
        
        test_db.add_all([spell1, spell2])
        await test_db.commit()
        
        matcher = MatcherService(test_db)
        
        # Query for TypeError spells
        candidates = await matcher._query_candidate_spells("typeerror")
        
        assert len(candidates) == 1
        assert candidates[0].id == spell1.id
    
    async def test_query_candidate_spells_returns_all_when_no_type(self, test_db):
        """Test that querying with no error type returns all spells."""
        # Create spells
        spell1 = Spell(
            title="Fix 1",
            description="Fix type errors",
            error_type="TypeError",
            error_pattern="error",
            solution_code="fix",
            tags="types"
        )
        spell2 = Spell(
            title="Fix 2",
            description="Fix syntax errors",
            error_type="SyntaxError",
            error_pattern="error",
            solution_code="fix",
            tags="syntax"
        )
        
        test_db.add_all([spell1, spell2])
        await test_db.commit()
        
        matcher = MatcherService(test_db)
        
        # Query with empty error type
        candidates = await matcher._query_candidate_spells("")
        
        assert len(candidates) == 2
    
    async def test_compute_similarity(self, test_db):
        """Test similarity score computation."""
        spell = Spell(
            title="Fix undefined",
            description="Handle undefined variable access",
            error_type="TypeError",
            error_pattern="undefined variable",
            solution_code="check undefined",
            tags="undefined"
        )
        
        matcher = MatcherService(test_db)
        
        # Error with matching keywords
        error = {
            "error_type": "typeerror",
            "message": "undefined variable access",
            "context": "variable property"
        }
        
        score = await matcher._compute_similarity(error, spell)
        
        # Should have positive similarity due to matching keywords
        assert score > 0.0
        assert score <= 1.0
    
    async def test_compute_similarity_with_type_boost(self, test_db):
        """Test that matching error types boost similarity score."""
        spell = Spell(
            title="Fix error",
            description="Handle errors",
            error_type="TypeError",
            error_pattern="error",
            solution_code="fix",
            tags="error"
        )
        
        matcher = MatcherService(test_db)
        
        # Error with matching type
        error_with_type = {
            "error_type": "typeerror",
            "message": "error message",
            "context": ""
        }
        
        # Error without matching type
        error_without_type = {
            "error_type": "syntaxerror",
            "message": "error message",
            "context": ""
        }
        
        score_with_type = await matcher._compute_similarity(error_with_type, spell)
        score_without_type = await matcher._compute_similarity(error_without_type, spell)
        
        # Score with matching type should be higher
        assert score_with_type > score_without_type
    
    async def test_extract_keywords(self, test_db):
        """Test keyword extraction from text."""
        matcher = MatcherService(test_db)
        
        text = "Cannot read property 'length' of undefined variable"
        keywords = matcher._extract_keywords(text)
        
        # Should extract meaningful keywords
        assert "cannot" in keywords
        assert "read" in keywords
        assert "property" in keywords
        assert "length" in keywords
        assert "undefined" in keywords
        assert "variable" in keywords
        
        # Should filter out stop words
        assert "of" not in keywords
    
    async def test_match_spells_handles_exceptions_gracefully(self, test_db):
        """Test that match_spells returns empty list on exceptions."""
        matcher = MatcherService(test_db)
        
        # Invalid error payload that might cause issues
        error_payload = None
        
        # Should not raise exception, return empty list
        result = await matcher.match_spells(error_payload)
        assert result == []
