"""
Patch Generator Service for adapting spells to specific codebases.

This module provides functionality to generate context-aware patches by adapting
canonical spell solutions to specific failing code scenarios using LLM providers.
"""

import logging
import re
from typing import Dict, List, Optional
from collections import Counter

from app.models.spell import Spell
from app.models.spell_application import (
    FailingContext,
    AdaptationConstraints,
    PatchResult
)
from app.services.llm_service import LLMService
from app.utils.logging import safe_log_data

logger = logging.getLogger(__name__)


class PatchGeneratorService:
    """
    Service for generating adapted patches from spells.
    
    Takes a canonical spell solution and adapts it to a specific codebase
    context by using LLM providers to generate git unified diff patches.
    
    Attributes:
        llm_service: LLM service instance for generating patches
    """
    
    def __init__(self, llm_service: LLMService):
        """
        Initialize Patch Generator Service.
        
        Args:
            llm_service: LLM service instance for patch generation
        """
        self.llm_service = llm_service
        logger.info(
            "Patch Generator Service initialized",
            extra={
                "service": "patch_generator",
                "llm_provider": llm_service.provider
            }
        )
    
    def _build_prompt(
        self,
        spell: Spell,
        failing_context: FailingContext,
        constraints: AdaptationConstraints
    ) -> str:
        """
        Construct LLM prompt for patch generation.
        
        Builds a comprehensive prompt that includes:
        - System instructions for JSON output
        - Failing context (language, version, test, stack trace, commit SHA)
        - Spell incantation (canonical solution)
        - Adaptation constraints (max files, excluded patterns, style preservation)
        
        Args:
            spell: Spell with canonical solution (incantation)
            failing_context: Context about the failing code
            constraints: Constraints for patch adaptation
            
        Returns:
            Formatted prompt string for LLM
        """
        # Build system prompt
        system_prompt = """You are Kiro — an automated code patch generator. You will be given:
(1) failing context (stack trace, failing test name, repo language & version)
(2) a canonical spell incantation (git diff or code solution)
(3) adaptation constraints

Produce a git unified diff that applies to the repository at the specified commit SHA.

Do not output anything other than: a JSON object with keys "patch" (string with unified git diff), "files_touched" (list of paths), and "rationale" (short, 1-2 lines).

Do NOT include explanations outside the JSON. If unable, return {"error": "..."}."""
        
        # Build context section
        context_parts = [
            f"- repository: {failing_context.repository}",
            f"- commit_sha: {failing_context.commit_sha}"
        ]
        
        if failing_context.language:
            context_parts.append(f"- language: {failing_context.language}")
        
        if failing_context.version:
            context_parts.append(f"- version: {failing_context.version}")
        
        if failing_context.failing_test:
            context_parts.append(f"- failing_test: {failing_context.failing_test}")
        
        if failing_context.stack_trace:
            context_parts.append(f"- stack_trace: {failing_context.stack_trace}")
        
        context_section = "\n".join(context_parts)
        
        # Build constraints section
        constraints_parts = [
            f"- Limit changes to at most {constraints.max_files} files"
        ]
        
        if constraints.preserve_style:
            constraints_parts.append("- Keep coding style intact")
        
        if constraints.excluded_patterns:
            excluded = ", ".join(constraints.excluded_patterns)
            constraints_parts.append(f"- Do not change: {excluded}")
        
        constraints_section = "\n".join(constraints_parts)
        
        # Build full prompt
        prompt = f"""{system_prompt}

Context:
{context_section}

Spell (incantation):
{spell.solution_code}

Constraints:
{constraints_section}

Return:
{{"patch": "...git diff...", "files_touched": ["..."], "rationale": "..."}}"""
        
        return prompt
    
    def _infer_language(self, spell: Spell) -> Optional[str]:
        """
        Infer programming language from spell incantation.
        
        Extracts file extensions from the spell's solution code and maps
        them to programming languages. Returns the most common language
        found, or None if no language can be inferred.
        
        Args:
            spell: Spell with solution code containing file paths
            
        Returns:
            Inferred language name (e.g., "python", "javascript") or None
        """
        # Extension to language mapping
        extension_map = {
            "py": "python",
            "js": "javascript",
            "jsx": "javascript",
            "ts": "typescript",
            "tsx": "typescript",
            "java": "java",
            "cpp": "cpp",
            "c": "c",
            "h": "c",
            "hpp": "cpp",
            "cs": "csharp",
            "rb": "ruby",
            "go": "go",
            "rs": "rust",
            "php": "php",
            "swift": "swift",
            "kt": "kotlin",
            "scala": "scala",
            "r": "r",
            "m": "objective-c",
            "sh": "bash",
            "bash": "bash",
            "sql": "sql",
            "html": "html",
            "css": "css",
            "scss": "css",
            "sass": "css",
            "json": "json",
            "xml": "xml",
            "yaml": "yaml",
            "yml": "yaml",
            "md": "markdown",
        }
        
        # Extract file extensions from solution code
        # Look for patterns like: filename.ext, /path/to/file.ext, etc.
        pattern = r'\b[\w/\-\.]+\.(\w+)\b'
        matches = re.findall(pattern, spell.solution_code)
        
        if not matches:
            return None
        
        # Map extensions to languages
        languages = []
        for ext in matches:
            ext_lower = ext.lower()
            if ext_lower in extension_map:
                languages.append(extension_map[ext_lower])
        
        if not languages:
            return None
        
        # Return most common language
        language_counts = Counter(languages)
        most_common = language_counts.most_common(1)
        
        return most_common[0][0] if most_common else None
    
    def _validate_patch(
        self,
        patch: str,
        files_touched: List[str],
        constraints: AdaptationConstraints
    ) -> tuple[bool, Optional[str]]:
        """
        Validate patch format and constraint compliance.
        
        Validates:
        - Git diff header format (starts with "diff --git")
        - Unified diff markers (+++, ---, @@)
        - File paths consistency between patch and files_touched
        - Constraint compliance (max files limit)
        
        Args:
            patch: Git unified diff string
            files_touched: List of file paths modified in patch
            constraints: Adaptation constraints to validate against
            
        Returns:
            Tuple of (is_valid, error_message)
            - is_valid: True if patch is valid, False otherwise
            - error_message: Description of validation failure, or None if valid
        """
        # Validate git diff header format
        if not patch.strip().startswith("diff --git"):
            return False, "Patch must start with valid git diff header (diff --git)"
        
        # Validate unified diff markers are present
        has_file_markers = ("+++" in patch and "---" in patch)
        has_hunk_markers = "@@" in patch
        
        if not (has_file_markers and has_hunk_markers):
            return False, "Patch must contain valid unified diff markers (+++, ---, @@)"
        
        # Validate constraint compliance - max files
        if len(files_touched) > constraints.max_files:
            return False, f"Patch modifies {len(files_touched)} files, exceeds limit of {constraints.max_files}"
        
        # Extract file paths from patch headers
        # Look for patterns like: diff --git a/path/to/file b/path/to/file
        patch_file_pattern = r'diff --git a/([\S]+) b/([\S]+)'
        patch_files = set()
        
        for match in re.finditer(patch_file_pattern, patch):
            # Use the 'b/' path (after modification)
            patch_files.add(match.group(2))
        
        # Validate file paths consistency
        files_touched_set = set(files_touched)
        
        # Check if all files in patch are in files_touched
        missing_files = patch_files - files_touched_set
        if missing_files:
            return False, f"Patch contains files not listed in files_touched: {', '.join(missing_files)}"
        
        return True, None
    
    async def generate_patch(
        self,
        spell: Spell,
        failing_context: FailingContext,
        constraints: AdaptationConstraints
    ) -> PatchResult:
        """
        Generate adapted patch using LLM.
        
        Main method that orchestrates the patch generation process:
        1. Infer language if not provided in context
        2. Build LLM prompt with context, spell, and constraints
        3. Call LLM service to generate patch
        4. Parse JSON response
        5. Validate patch format and constraints
        6. Return PatchResult or raise appropriate error
        
        Args:
            spell: Spell with canonical solution to adapt
            failing_context: Context about the failing code
            constraints: Constraints for patch adaptation
            
        Returns:
            PatchResult with patch, files_touched, and rationale
            
        Raises:
            ValueError: If patch validation fails or LLM returns error
            Exception: If LLM API call fails
        """
        # Log request parameters (with redaction)
        logger.info(
            "Starting patch generation",
            extra={
                "service": "patch_generator",
                "spell_id": spell.id,
                "repository": failing_context.repository,
                "commit_sha": failing_context.commit_sha,
                "language": failing_context.language,
                "version": failing_context.version,
                "max_files": constraints.max_files,
                "preserve_style": constraints.preserve_style
            }
        )
        
        # Infer language if not provided
        if not failing_context.language:
            inferred_language = self._infer_language(spell)
            if inferred_language:
                # Create a new context with inferred language
                failing_context = FailingContext(
                    repository=failing_context.repository,
                    commit_sha=failing_context.commit_sha,
                    language=inferred_language,
                    version=failing_context.version,
                    failing_test=failing_context.failing_test,
                    stack_trace=failing_context.stack_trace
                )
                logger.info(
                    "Inferred language from spell incantation",
                    extra={
                        "service": "patch_generator",
                        "spell_id": spell.id,
                        "inferred_language": inferred_language
                    }
                )
        
        # Build LLM prompt
        prompt = self._build_prompt(spell, failing_context, constraints)
        
        # Log prompt construction (redacted)
        logger.debug(
            "Built LLM prompt for patch generation",
            extra={
                "service": "patch_generator",
                "spell_id": spell.id,
                "prompt_length": len(prompt),
                "has_stack_trace": bool(failing_context.stack_trace),
                "has_failing_test": bool(failing_context.failing_test)
            }
        )
        
        # Call LLM service
        try:
            logger.debug(
                "Calling LLM service for patch generation",
                extra={
                    "service": "patch_generator",
                    "spell_id": spell.id,
                    "timeout": 30
                }
            )
            response = await self.llm_service.generate_patch(prompt, timeout=30)
            
            # Log response metadata (redacted)
            logger.info(
                "Received LLM response",
                extra={
                    "service": "patch_generator",
                    "spell_id": spell.id,
                    "has_error": "error" in response,
                    "response_keys": list(response.keys())
                }
            )
            
        except Exception as e:
            logger.error(
                "LLM API call failed",
                exc_info=True,
                extra={
                    "service": "patch_generator",
                    "spell_id": spell.id,
                    "error_type": type(e).__name__,
                    "error_message": safe_log_data(str(e))
                }
            )
            raise Exception(f"Failed to generate patch: {str(e)}")
        
        # Check for error in response
        if "error" in response:
            error_msg = response["error"]
            logger.error(
                "LLM returned error response",
                extra={
                    "service": "patch_generator",
                    "spell_id": spell.id,
                    "error_message": safe_log_data(error_msg)
                }
            )
            raise ValueError(f"LLM failed to generate patch: {error_msg}")
        
        # Parse response
        try:
            patch = response["patch"]
            files_touched = response["files_touched"]
            rationale = response["rationale"]
            
            logger.debug(
                "Parsed LLM response fields",
                extra={
                    "service": "patch_generator",
                    "spell_id": spell.id,
                    "patch_length": len(patch),
                    "files_count": len(files_touched),
                    "rationale_length": len(rationale)
                }
            )
            
        except KeyError as e:
            logger.error(
                "LLM response missing required field",
                extra={
                    "service": "patch_generator",
                    "spell_id": spell.id,
                    "missing_field": str(e),
                    "available_fields": list(response.keys())
                }
            )
            raise ValueError(f"Invalid LLM response: missing field {e}")
        
        # Validate patch format and constraints
        logger.debug(
            "Validating patch format and constraints",
            extra={
                "service": "patch_generator",
                "spell_id": spell.id,
                "files_count": len(files_touched),
                "max_files_constraint": constraints.max_files
            }
        )
        
        is_valid, error_message = self._validate_patch(patch, files_touched, constraints)
        
        if not is_valid:
            logger.error(
                "Patch validation failed",
                extra={
                    "service": "patch_generator",
                    "spell_id": spell.id,
                    "validation_error": error_message,
                    "files_count": len(files_touched),
                    "max_files": constraints.max_files
                }
            )
            raise ValueError(f"Patch validation failed: {error_message}")
        
        logger.info(
            "Successfully generated and validated patch",
            extra={
                "service": "patch_generator",
                "spell_id": spell.id,
                "files_touched_count": len(files_touched),
                "files_touched": files_touched,
                "patch_size_bytes": len(patch.encode('utf-8'))
            }
        )
        
        # Return PatchResult
        return PatchResult(
            patch=patch,
            files_touched=files_touched,
            rationale=rationale
        )
