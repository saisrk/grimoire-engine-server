"""
Spell Generator Service.

This module handles automatic creation of spells when no matches are found.
It uses LLM services to generate human-readable content and creates spell records.
"""

import logging
import os
from typing import Any, Dict, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.spell import Spell
from app.services.llm_service import get_llm_service

logger = logging.getLogger(__name__)


class SpellGeneratorService:
    """
    Service for automatically generating spells from error patterns.
    
    This service orchestrates:
    1. Checking if auto-generation is enabled
    2. Calling LLM service to generate content
    3. Creating spell record in database
    4. Logging and telemetry
    
    Attributes:
        db: Database session
        llm_service: LLM service instance
        auto_create_enabled: Whether auto-creation is enabled
    """
    
    def __init__(
        self,
        db: AsyncSession,
        llm_service: Optional[Any] = None,
        auto_create_enabled: Optional[bool] = None
    ):
        """
        Initialize Spell Generator Service.
        
        Args:
            db: Async SQLAlchemy database session
            llm_service: Optional LLM service instance. Creates default if None.
            auto_create_enabled: Override for auto-creation flag. Uses env var if None.
        """
        self.db = db
        self.llm_service = llm_service or get_llm_service()
        
        # Check if auto-creation is enabled
        if auto_create_enabled is not None:
            self.auto_create_enabled = auto_create_enabled
        else:
            env_value = os.getenv("AUTO_CREATE_SPELLS", "false").lower()
            self.auto_create_enabled = env_value in ("true", "1", "yes")
        
        logger.info(
            f"Spell Generator initialized: auto_create={self.auto_create_enabled}"
        )
    
    async def generate_spell(
        self,
        error_payload: Dict[str, Any],
        pr_context: Optional[Dict[str, Any]] = None
    ) -> Optional[int]:
        """
        Generate and create a new spell from error payload.
        
        This is the main entry point for automatic spell generation.
        Checks if auto-creation is enabled, generates content using LLM,
        and creates the spell in the database.
        
        Args:
            error_payload: Dictionary with error information:
                - error_type: Type of error
                - message: Error message
                - context: Code context
                - stack_trace: Stack trace (optional)
            pr_context: Optional PR context with:
                - repo: Repository name
                - pr_number: PR number
                - files_changed: List of changed files
                
        Returns:
            Spell ID if created successfully, None otherwise
            
        Example:
            generator = SpellGeneratorService(db)
            error = {
                "error_type": "TypeError",
                "message": "Cannot read property 'length' of undefined",
                "context": "const len = myArray.length;"
            }
            spell_id = await generator.generate_spell(error)
            # Returns: 42 (new spell ID)
        """
        # Check if auto-creation is enabled
        if not self.auto_create_enabled:
            logger.debug("Auto-creation disabled, skipping spell generation")
            return None
        
        try:
            logger.info(
                "Generating new spell",
                extra={
                    "error_type": error_payload.get("error_type"),
                    "has_pr_context": pr_context is not None
                }
            )
            
            # Generate content using LLM
            content = await self.llm_service.generate_spell_content(
                error_payload,
                pr_context
            )
            
            # Extract error pattern from payload
            error_pattern = self._extract_error_pattern(error_payload)
            
            # Generate tags from error and context
            tags = self._generate_tags(error_payload, pr_context)
            
            # Create spell in database
            spell_id = await self._create_spell_record(
                title=content["title"],
                description=content["description"],
                error_type=error_payload.get("error_type", "Unknown"),
                error_pattern=error_pattern,
                solution_code=content["solution_code"],
                tags=tags,
                confidence_score=content["confidence_score"]
            )
            
            logger.info(
                f"Successfully created auto-generated spell: {spell_id}",
                extra={
                    "spell_id": spell_id,
                    "confidence": content["confidence_score"],
                    "error_type": error_payload.get("error_type")
                }
            )
            
            return spell_id
            
        except Exception as e:
            logger.error(
                f"Error generating spell: {e}",
                exc_info=True,
                extra={
                    "error_type": error_payload.get("error_type"),
                    "has_pr_context": pr_context is not None
                }
            )
            return None
    
    def _extract_error_pattern(self, error_payload: Dict[str, Any]) -> str:
        """
        Extract error pattern from error payload.
        
        Creates a regex-like pattern that can match similar errors.
        
        Args:
            error_payload: Error information
            
        Returns:
            Error pattern string
            
        Example:
            pattern = generator._extract_error_pattern({
                "error_type": "TypeError",
                "message": "Cannot read property 'length' of undefined"
            })
            # Returns: "Cannot read property .* of undefined"
        """
        message = error_payload.get("message", "")
        
        if not message:
            return ".*"
        
        # Simple pattern extraction: replace specific values with wildcards
        # This is a basic implementation - can be enhanced with more sophisticated logic
        import re
        
        # Replace quoted strings with wildcards
        pattern = re.sub(r"'[^']*'", "'.*'", message)
        pattern = re.sub(r'"[^"]*"', '".*"', pattern)
        
        # Replace numbers with wildcards
        pattern = re.sub(r'\b\d+\b', r'\\d+', pattern)
        
        return pattern
    
    def _generate_tags(
        self,
        error_payload: Dict[str, Any],
        pr_context: Optional[Dict[str, Any]]
    ) -> str:
        """
        Generate tags from error and PR context.
        
        Args:
            error_payload: Error information
            pr_context: Optional PR context
            
        Returns:
            Comma-separated tags string
            
        Example:
            tags = generator._generate_tags(
                {"error_type": "TypeError"},
                {"files_changed": ["app/main.py", "tests/test.js"]}
            )
            # Returns: "typeerror,python,javascript,auto-generated"
        """
        tags = set()
        
        # Add error type as tag
        error_type = error_payload.get("error_type", "").lower()
        if error_type:
            tags.add(error_type)
        
        # Add language tags from file extensions
        if pr_context and pr_context.get("files_changed"):
            for file_path in pr_context["files_changed"]:
                ext = file_path.split(".")[-1].lower()
                if ext in ["py", "js", "ts", "java", "go", "rb", "php", "cpp", "c"]:
                    tags.add(ext)
        
        # Add auto-generated tag
        tags.add("auto-generated")
        
        return ",".join(sorted(tags))
    
    async def _create_spell_record(
        self,
        title: str,
        description: str,
        error_type: str,
        error_pattern: str,
        solution_code: str,
        tags: str,
        confidence_score: int
    ) -> int:
        """
        Create spell record in database.
        
        Args:
            title: Spell title
            description: Spell description
            error_type: Error type
            error_pattern: Error pattern regex
            solution_code: Solution code
            tags: Comma-separated tags
            confidence_score: Confidence score (0-100)
            
        Returns:
            Created spell ID
            
        Raises:
            Exception: If database operation fails
        """
        spell = Spell(
            title=title,
            description=description,
            error_type=error_type,
            error_pattern=error_pattern,
            solution_code=solution_code,
            tags=tags,
            auto_generated=1,
            confidence_score=confidence_score,
            human_reviewed=0
        )
        
        self.db.add(spell)
        await self.db.commit()
        await self.db.refresh(spell)
        
        logger.debug(
            f"Created spell record in database: {spell.id}",
            extra={"spell_id": spell.id, "title": title}
        )
        
        return spell.id
