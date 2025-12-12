"""
Matcher Service.

This module handles matching error payloads with relevant spells from the database.
It extracts error characteristics, queries candidate spells, computes similarity scores,
and returns a ranked list of spell IDs.
"""

import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.spell import Spell
from app.models.repository_config import RepositoryConfig

logger = logging.getLogger(__name__)


class MatcherService:
    """
    Service for matching errors with relevant spells.
    
    This class implements the spell matching workflow:
    1. Extract error characteristics from error payload
    2. Query database for candidate spells
    3. Compute similarity scores between error and each spell
    4. Rank spells by similarity score
    5. Return sorted list of spell IDs
    
    Current implementation uses simple keyword matching for similarity.
    Future enhancements will integrate vector databases for semantic similarity.
    
    Attributes:
        db: Async SQLAlchemy database session
    """
    
    def __init__(self, db: AsyncSession):
        """
        Initialize Matcher Service.
        
        Args:
            db: Async SQLAlchemy database session for querying spells
        """
        self.db = db
    
    async def match_spells(
        self, 
        error_payload: Dict[str, Any],
        repository_context: Optional[Dict[str, Any]] = None
    ) -> List[int]:
        """
        Match error payload with relevant spells and return ranked IDs.
        
        Orchestrates the complete matching workflow:
        1. Extract error characteristics (type, message, context)
        2. Query database for candidate spells based on error type
        3. Compute similarity score for each candidate spell
        4. Sort spells by similarity score descending
        5. Return list of spell IDs
        
        Args:
            error_payload: Dictionary containing error information with keys:
                - error_type: Type of error (e.g., "TypeError", "SyntaxError")
                - message: Error message text
                - context: Optional code context where error occurred
                - stack_trace: Optional stack trace (not currently used)
            repository_context: Optional repository context with keys:
                - repo: Repository name (e.g., "owner/repo")
                - pr_number: Pull request number
                - files_changed: List of changed files
                
        Returns:
            List of spell IDs sorted by relevance (highest score first).
            Returns empty list if no matching spells are found.
            
        Example:
            matcher = MatcherService(db)
            error = {
                "error_type": "TypeError",
                "message": "Cannot read property 'length' of undefined",
                "context": "const len = myArray.length;"
            }
            spell_ids = await matcher.match_spells(error)
            # Returns: [5, 12, 3]  # Spell IDs ranked by relevance
            
        Extension Points:
            TODO: Vector DB Integration
            - Replace keyword matching with semantic similarity using embeddings
            - Generate embeddings for error description using OpenAI/Cohere API
            - Query vector database (pgvector, Qdrant, Pinecone) for similar spell embeddings
            - Use cosine similarity for semantic matching
            - Combine keyword and vector scores for hybrid search
            - Implementation steps:
              1. Add embedding generation function
              2. Store spell embeddings in vector DB on creation
              3. Replace _compute_similarity() with vector similarity query
              4. Add embedding column to Spell model
              5. Implement hybrid scoring (keyword + vector)
            
            TODO: Kiro Vibe-Code Integration
            - Use Kiro's code understanding for context-aware matching
            - Analyze codebase structure and patterns
            - Consider project-specific conventions and styles
            - Rank spells based on project context fit
            - Integrate with Kiro IDE for seamless developer experience
            - Implementation steps:
              1. Add Kiro API client
              2. Send error context to Kiro for analysis
              3. Receive Kiro's code understanding insights
              4. Adjust spell ranking based on project context
              5. Provide IDE integration hooks for spell application
            - Kiro features to leverage:
              * Code pattern recognition
              * Project-specific style analysis
              * Dependency and import understanding
              * Test coverage awareness
            
            TODO: MCP Analyzer Integration
            - Use MCP protocol to analyze error context
            - Call MCP servers for deeper code analysis
            - Extract semantic patterns beyond surface-level matching
            - Improve matching accuracy with static analysis insights
            - Implementation steps:
              1. Add MCP client library
              2. Configure MCP analyzer endpoints
              3. Send error context to MCP for analysis
              4. Parse MCP response for additional error characteristics
              5. Incorporate MCP insights into similarity scoring
        """
        try:
            # Extract error characteristics from payload
            error_characteristics = self._extract_error_characteristics(error_payload)
            
            logger.info(
                "Matching spells for error",
                extra={
                    "error_type": error_characteristics.get("error_type"),
                    "message_length": len(error_characteristics.get("message", ""))
                }
            )
            
            # Query database for candidate spells based on error type and repository context
            candidate_spells = await self._query_candidate_spells(
                error_characteristics.get("error_type"),
                repository_context
            )
            
            if not candidate_spells:
                logger.info("No candidate spells found for error type")
                return []
            
            logger.debug(f"Found {len(candidate_spells)} candidate spells")
            
            # Compute similarity scores for each candidate
            scored_spells: List[Tuple[int, float]] = []
            for spell in candidate_spells:
                similarity_score = await self._compute_similarity(
                    error_characteristics,
                    spell
                )
                scored_spells.append((spell.id, similarity_score))
                logger.debug(
                    f"Spell {spell.id} ({spell.title}): similarity={similarity_score:.3f}"
                )
            
            # Sort by similarity score descending
            scored_spells.sort(key=lambda x: x[1], reverse=True)
            
            # Extract just the spell IDs
            ranked_spell_ids = [spell_id for spell_id, score in scored_spells]
            
            logger.info(
                f"Matched {len(ranked_spell_ids)} spells",
                extra={"top_spell_id": ranked_spell_ids[0] if ranked_spell_ids else None}
            )
            
            return ranked_spell_ids
            
        except Exception as e:
            logger.error(
                f"Error matching spells: {e}",
                exc_info=True,
                extra={"error_payload_keys": list(error_payload.keys()) if error_payload else None}
            )
            # Return empty list on error rather than raising
            return []
    
    def _extract_error_characteristics(
        self,
        error_payload: Dict[str, Any]
    ) -> Dict[str, str]:
        """
        Extract error characteristics from error payload.
        
        Parses the error payload to extract key characteristics that will be
        used for matching: error type, message, and context.
        
        Args:
            error_payload: Dictionary containing error information
            
        Returns:
            Dictionary with extracted characteristics:
                - error_type: Type of error (normalized)
                - message: Error message text
                - context: Code context where error occurred
                
        Example:
            payload = {
                "error_type": "TypeError",
                "message": "Cannot read property 'length' of undefined",
                "context": "const len = myArray.length;",
                "stack_trace": "..."
            }
            characteristics = matcher._extract_error_characteristics(payload)
            # Returns: {
            #     "error_type": "typeerror",
            #     "message": "cannot read property length of undefined",
            #     "context": "const len myarray length"
            # }
        """
        # Extract and normalize error type
        error_type = error_payload.get("error_type", "").lower().strip()
        
        # Extract and normalize message
        message = error_payload.get("message", "").lower().strip()
        
        # Extract and normalize context
        context = error_payload.get("context", "").lower().strip()
        
        logger.debug(
            "Extracted error characteristics",
            extra={
                "error_type": error_type,
                "has_message": bool(message),
                "has_context": bool(context)
            }
        )
        
        return {
            "error_type": error_type,
            "message": message,
            "context": context
        }
    
    async def _query_candidate_spells(
        self,
        error_type: str,
        repository_context: Optional[Dict[str, Any]] = None
    ) -> List[Spell]:
        """
        Query database for candidate spells based on error type and repository context.
        
        Retrieves spells from the database that match the given error type.
        If repository_context is provided, prioritizes spells from the same repository.
        If error_type is empty or None, returns all spells.
        
        Args:
            error_type: Normalized error type string
            repository_context: Optional repository context for filtering
            
        Returns:
            List of Spell objects that match the error type, prioritized by repository
            
        Example:
            spells = await matcher._query_candidate_spells("typeerror", {"repo": "owner/repo"})
            # Returns: [Spell(id=1, error_type="TypeError", ...), ...]
        """
        try:
            # Build base query for spells with error type filter
            if error_type:
                stmt = select(Spell).where(
                    Spell.error_type.ilike(f"%{error_type}%")
                )
            else:
                stmt = select(Spell)
            
            # If repository context is provided, prioritize spells from the same repository
            if repository_context and repository_context.get("repo"):
                repo_name = repository_context["repo"]
                
                # First, try to get spells from the same repository
                repo_stmt = (
                    stmt.join(RepositoryConfig)
                    .where(RepositoryConfig.repo_name == repo_name)
                )
                
                repo_result = await self.db.execute(repo_stmt)
                repo_spells = list(repo_result.scalars().all())
                
                if repo_spells:
                    logger.debug(
                        f"Found {len(repo_spells)} spells from same repository: {repo_name}",
                        extra={"error_type": error_type, "repo": repo_name}
                    )
                    return repo_spells
                
                logger.debug(
                    f"No spells found in repository {repo_name}, querying all repositories",
                    extra={"error_type": error_type, "repo": repo_name}
                )
            
            # Fallback to all spells if no repository-specific spells found
            result = await self.db.execute(stmt)
            spells = result.scalars().all()
            
            logger.debug(
                f"Queried {len(spells)} candidate spells",
                extra={"error_type": error_type}
            )
            
            return list(spells)
            
        except Exception as e:
            logger.error(
                f"Error querying candidate spells: {e}",
                exc_info=True,
                extra={"error_type": error_type}
            )
            return []
    
    async def _compute_similarity(
        self,
        error: Dict[str, str],
        spell: Spell
    ) -> float:
        """
        Compute similarity score between error and spell.
        
        Current implementation uses simple keyword matching:
        1. Extract keywords from error message and context
        2. Extract keywords from spell description and error pattern
        3. Compute keyword overlap score
        4. Return normalized similarity score (0.0 to 1.0)
        
        Future implementation will use vector embeddings and cosine similarity
        for semantic matching.
        
        Args:
            error: Dictionary with error characteristics (type, message, context)
            spell: Spell object from database
            
        Returns:
            Similarity score between 0.0 (no match) and 1.0 (perfect match)
            
        Example:
            error = {
                "error_type": "typeerror",
                "message": "cannot read property length of undefined",
                "context": "const len myarray length"
            }
            spell = Spell(
                error_type="TypeError",
                description="Fix undefined array access",
                error_pattern="undefined.*property"
            )
            score = await matcher._compute_similarity(error, spell)
            # Returns: 0.65
            
        Algorithm:
            1. Tokenize error message and context into keywords
            2. Tokenize spell description and error pattern into keywords
            3. Count matching keywords
            4. Normalize by total unique keywords
            5. Apply boost if error types match exactly
            
        TODO: Vector DB Enhancement
        - Generate embeddings for error description using OpenAI/Cohere
        - Query vector database for similar spell embeddings
        - Use cosine similarity: similarity = dot(error_emb, spell_emb) / (||error_emb|| * ||spell_emb||)
        - Combine with keyword score for hybrid matching
        - Example: final_score = 0.7 * vector_score + 0.3 * keyword_score
        """
        # Extract keywords from error
        error_keywords = self._extract_keywords(
            error.get("message", "") + " " + error.get("context", "")
        )
        
        # Extract keywords from spell
        spell_keywords = self._extract_keywords(
            spell.description.lower() + " " + spell.error_pattern.lower()
        )
        
        # If either has no keywords, return 0
        if not error_keywords or not spell_keywords:
            return 0.0
        
        # Compute keyword overlap
        matching_keywords = error_keywords.intersection(spell_keywords)
        total_keywords = error_keywords.union(spell_keywords)
        
        # Calculate base similarity score (Jaccard similarity)
        if len(total_keywords) == 0:
            base_score = 0.0
        else:
            base_score = len(matching_keywords) / len(total_keywords)
        
        # Apply boost if error types match
        error_type_boost = 0.0
        if error.get("error_type") and spell.error_type.lower() == error.get("error_type"):
            error_type_boost = 0.2
        
        # Combine scores (cap at 1.0)
        final_score = min(base_score + error_type_boost, 1.0)
        
        logger.debug(
            f"Similarity computed for spell {spell.id}",
            extra={
                "base_score": base_score,
                "error_type_boost": error_type_boost,
                "final_score": final_score,
                "matching_keywords": len(matching_keywords),
                "total_keywords": len(total_keywords)
            }
        )
        
        return final_score
    
    def _extract_keywords(self, text: str) -> set:
        """
        Extract keywords from text for matching.
        
        Tokenizes text into words, removes common stop words and punctuation,
        and returns a set of meaningful keywords.
        
        Args:
            text: Input text to extract keywords from
            
        Returns:
            Set of keyword strings
            
        Example:
            keywords = matcher._extract_keywords(
                "Cannot read property 'length' of undefined"
            )
            # Returns: {"cannot", "read", "property", "length", "undefined"}
        """
        # Convert to lowercase
        text = text.lower()
        
        # Remove punctuation and split into words
        words = re.findall(r'\b\w+\b', text)
        
        # Common stop words to filter out
        stop_words = {
            "a", "an", "and", "are", "as", "at", "be", "by", "for",
            "from", "has", "he", "in", "is", "it", "its", "of", "on",
            "that", "the", "to", "was", "will", "with"
        }
        
        # Filter out stop words and very short words
        keywords = {
            word for word in words
            if word not in stop_words and len(word) > 2
        }
        
        return keywords
