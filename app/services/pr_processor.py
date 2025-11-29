"""
PR Processor Service.

This module handles processing of GitHub pull request webhook events,
including fetching PR diffs from the GitHub API and parsing them to
extract file changes and error patterns.
"""

import logging
import os
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)


class PRProcessor:
    """
    Service for processing GitHub pull request events.
    
    This class orchestrates the workflow of:
    1. Extracting PR metadata from webhook payloads
    2. Fetching PR diffs from GitHub API
    3. Parsing diffs to extract file changes
    4. [Extension Point] Extracting error patterns using MCP analyzers
    5. [Extension Point] Running code in sandbox environment
    
    Attributes:
        github_token: GitHub API token for authenticated requests
        timeout: HTTP request timeout in seconds
    """
    
    def __init__(self, github_token: Optional[str] = None, timeout: int = 30):
        """
        Initialize PR Processor.
        
        Args:
            github_token: GitHub API token. If None, reads from GITHUB_API_TOKEN env var
            timeout: HTTP request timeout in seconds (default: 30)
        """
        self.github_token = github_token or os.getenv("GITHUB_API_TOKEN")
        self.timeout = timeout
        
        # TODO: Authentication setup
        # For production, consider using GitHub App installation tokens
        # which provide better security and rate limits than personal access tokens.
        # See: https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app
        
        if not self.github_token:
            logger.warning(
                "GITHUB_API_TOKEN not configured. "
                "PR diff fetching will fail without authentication."
            )
    
    async def process_pr_event(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process GitHub pull request webhook event.
        
        Orchestrates the complete PR processing workflow:
        1. Extract repository name and PR number from webhook payload
        2. Fetch PR diff from GitHub API
        3. Parse diff to extract changed files
        4. [TODO: Extract error patterns using MCP analyzers]
        5. [TODO: Trigger matcher service with errors]
        
        Args:
            payload: GitHub webhook payload dictionary
            
        Returns:
            Dictionary containing processing results:
                - repo: Repository full name (owner/repo)
                - pr_number: Pull request number
                - files_changed: List of changed file paths
                - status: Processing status ("success" or "error")
                - error: Error message if status is "error"
                
        Example:
            processor = PRProcessor()
            result = await processor.process_pr_event(webhook_payload)
            # Returns: {
            #     "repo": "owner/repo",
            #     "pr_number": 123,
            #     "files_changed": ["app/main.py", "tests/test_main.py"],
            #     "status": "success"
            # }
            
        Extension Points:
            TODO: MCP Analyzer Integration
            - After parsing diff, send code changes to MCP analyzers
            - Use Model Context Protocol to analyze code for errors
            - Extract semantic error patterns beyond syntax
            - Call MCP servers for linting, type checking, static analysis
            - Normalize error formats across different analyzers
            
            TODO: Sandbox Runner Integration
            - Create isolated execution environment (Docker container)
            - Apply PR changes to codebase in sandbox
            - Run tests and capture errors, stack traces, failures
            - Parse test output for error patterns
            - Clean up sandbox after execution
            - Implement resource limits (CPU, memory, time)
            - Ensure network isolation and file system restrictions
        """
        try:
            # Extract repository name and PR number
            repo = payload.get("repository", {}).get("full_name")
            pr_number = payload.get("pull_request", {}).get("number")
            
            if not repo or not pr_number:
                logger.error(
                    "Missing required fields in webhook payload",
                    extra={"repo": repo, "pr_number": pr_number}
                )
                return {
                    "status": "error",
                    "error": "Missing repository or PR number in payload"
                }
            
            logger.info(f"Processing PR event: {repo}#{pr_number}")
            
            # Fetch PR diff from GitHub API
            diff = await self.fetch_pr_diff(repo, pr_number)
            
            if diff is None:
                return {
                    "repo": repo,
                    "pr_number": pr_number,
                    "status": "error",
                    "error": "Failed to fetch PR diff"
                }
            
            # Parse diff to extract file changes
            files_changed = self._parse_diff(diff)
            
            logger.info(
                f"Successfully processed PR {repo}#{pr_number}",
                extra={
                    "repo": repo,
                    "pr_number": pr_number,
                    "files_changed_count": len(files_changed)
                }
            )
            
            # TODO: Extract error patterns using MCP analyzers
            # errors = await self._extract_errors_with_mcp(files_changed, diff)
            
            # TODO: Trigger matcher service with extracted errors
            # matched_spells = await matcher_service.match_spells(errors)
            
            return {
                "repo": repo,
                "pr_number": pr_number,
                "files_changed": files_changed,
                "status": "success"
            }
            
        except Exception as e:
            logger.error(
                f"Error processing PR event: {e}",
                exc_info=True,
                extra={"payload_keys": list(payload.keys())}
            )
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def fetch_pr_diff(self, repo: str, pr_number: int) -> Optional[str]:
        """
        Fetch PR diff from GitHub API.
        
        Makes an authenticated HTTP request to the GitHub API to retrieve
        the diff for a specific pull request.
        
        Args:
            repo: Repository full name in format "owner/repo"
            pr_number: Pull request number
            
        Returns:
            PR diff as a string, or None if the request fails
            
        Example:
            diff = await processor.fetch_pr_diff("octocat/Hello-World", 123)
            
        GitHub API Documentation:
            https://docs.github.com/en/rest/pulls/pulls#get-a-pull-request
            
        TODO: Authentication Enhancement
        - Implement GitHub App installation token authentication
        - Add token refresh logic for long-running processes
        - Handle rate limit headers and implement backoff
        - Support multiple authentication methods (PAT, App, OAuth)
        
        TODO: Error Handling Enhancement
        - Implement exponential backoff for rate limit errors
        - Add retry logic for transient failures
        - Handle 404 (PR not found) vs 403 (permission denied) differently
        - Cache responses to reduce API calls
        """
        url = f"https://api.github.com/repos/{repo}/pulls/{pr_number}"
        
        headers = {
            "Accept": "application/vnd.github.v3.diff",
            "User-Agent": "Grimoire-Engine/0.1.0"
        }
        
        # Add authentication if token is available
        if self.github_token:
            headers["Authorization"] = f"Bearer {self.github_token}"
        else:
            logger.warning(
                "Fetching PR diff without authentication. "
                "Rate limits will be severely restricted."
            )
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                logger.debug(f"Fetching PR diff from: {url}")
                response = await client.get(url, headers=headers)
                
                # Check for rate limiting
                if response.status_code == 403:
                    rate_limit_remaining = response.headers.get("X-RateLimit-Remaining")
                    if rate_limit_remaining == "0":
                        reset_time = response.headers.get("X-RateLimit-Reset")
                        logger.error(
                            "GitHub API rate limit exceeded",
                            extra={
                                "reset_time": reset_time,
                                "repo": repo,
                                "pr_number": pr_number
                            }
                        )
                        return None
                
                # Raise for other HTTP errors
                response.raise_for_status()
                
                logger.debug(
                    f"Successfully fetched PR diff for {repo}#{pr_number}",
                    extra={"diff_size": len(response.text)}
                )
                
                return response.text
                
        except httpx.HTTPStatusError as e:
            logger.error(
                f"HTTP error fetching PR diff: {e.response.status_code}",
                extra={
                    "repo": repo,
                    "pr_number": pr_number,
                    "status_code": e.response.status_code,
                    "response_body": e.response.text[:200]  # Log first 200 chars
                }
            )
            return None
            
        except httpx.RequestError as e:
            logger.error(
                f"Network error fetching PR diff: {e}",
                extra={
                    "repo": repo,
                    "pr_number": pr_number,
                    "error_type": type(e).__name__
                }
            )
            return None
            
        except Exception as e:
            logger.error(
                f"Unexpected error fetching PR diff: {e}",
                exc_info=True,
                extra={"repo": repo, "pr_number": pr_number}
            )
            return None
    
    def _parse_diff(self, diff: str) -> List[str]:
        """
        Parse diff to extract changed file paths.
        
        Parses unified diff format to extract the list of files that were
        added, modified, or deleted in the pull request.
        
        Args:
            diff: Unified diff string from GitHub API
            
        Returns:
            List of file paths that were changed
            
        Example:
            diff = '''
            diff --git a/app/main.py b/app/main.py
            index abc123..def456 100644
            --- a/app/main.py
            +++ b/app/main.py
            @@ -1,3 +1,4 @@
            +import logging
             def main():
                 pass
            '''
            files = processor._parse_diff(diff)
            # Returns: ["app/main.py"]
            
        Diff Format:
            - Lines starting with "diff --git" indicate a new file
            - Format: "diff --git a/path/to/file b/path/to/file"
            - Extract the file path from the second occurrence (after "b/")
        """
        files_changed = []
        
        for line in diff.split("\n"):
            # Look for diff headers that indicate file changes
            if line.startswith("diff --git"):
                # Format: diff --git a/path/to/file b/path/to/file
                # Extract the file path from the "b/" part
                parts = line.split()
                if len(parts) >= 4:
                    # parts[3] is "b/path/to/file"
                    file_path = parts[3][2:]  # Remove "b/" prefix
                    files_changed.append(file_path)
                    logger.debug(f"Found changed file: {file_path}")
        
        logger.info(f"Parsed {len(files_changed)} changed files from diff")
        return files_changed
    
    # Extension point methods (stubs for future implementation)
    
    async def _extract_errors_with_mcp(
        self,
        files_changed: List[str],
        diff: str
    ) -> List[Dict[str, Any]]:
        """
        Extract error patterns using MCP analyzers.
        
        TODO: MCP Analyzer Integration
        
        This method will integrate with Model Context Protocol (MCP) servers
        to perform static analysis and error detection on the changed code.
        
        Implementation steps:
        1. Add MCP client library dependency
        2. Configure MCP server endpoints for different analyzers:
           - Python: pylint, mypy, ruff
           - JavaScript: ESLint, TypeScript compiler
           - General: CodeQL, Semgrep
        3. Send code changes to appropriate MCP analyzers based on file type
        4. Parse MCP responses to extract error information:
           - Error type (syntax, type, logic, security)
           - Error message and description
           - File location (line, column)
           - Severity level
           - Suggested fixes
        5. Normalize error formats across different analyzers
        6. Return structured error data for matching
        
        Args:
            files_changed: List of file paths that were modified
            diff: Complete diff string with code changes
            
        Returns:
            List of error dictionaries with structure:
                {
                    "error_type": str,
                    "message": str,
                    "file": str,
                    "line": int,
                    "column": int,
                    "severity": str,
                    "context": str
                }
                
        Example:
            errors = await processor._extract_errors_with_mcp(
                ["app/main.py"],
                diff_string
            )
            # Returns: [
            #     {
            #         "error_type": "TypeError",
            #         "message": "Argument of type 'str' cannot be assigned to parameter of type 'int'",
            #         "file": "app/main.py",
            #         "line": 42,
            #         "column": 15,
            #         "severity": "error",
            #         "context": "def process(value: int):\n    return value * 2"
            #     }
            # ]
        """
        # Placeholder implementation
        logger.debug("MCP analyzer integration not yet implemented")
        return []
    
    async def _run_in_sandbox(
        self,
        repo: str,
        pr_number: int,
        diff: str
    ) -> Dict[str, Any]:
        """
        Run code changes in isolated sandbox environment.
        
        TODO: Sandbox Runner Integration
        
        This method will create an isolated execution environment to test
        the PR changes and capture any runtime errors or test failures.
        
        Implementation steps:
        1. Choose sandbox technology:
           - Docker containers (good isolation, widely supported)
           - Firecracker microVMs (better security, faster startup)
           - gVisor (strong isolation, good performance)
        2. Create sandbox with base environment for the project
        3. Clone repository and checkout base branch
        4. Apply PR diff to the codebase
        5. Install dependencies
        6. Run test suite and capture output
        7. Parse test results for errors and failures
        8. Extract stack traces and error messages
        9. Clean up sandbox resources
        10. Return structured error data
        
        Security considerations:
        - Resource limits: CPU (1 core), memory (2GB), time (5 minutes)
        - Network isolation: No outbound connections except package registries
        - File system restrictions: Read-only base system, writable workspace
        - Process limits: Maximum number of processes
        - Disk space limits: Maximum workspace size
        
        Args:
            repo: Repository full name
            pr_number: Pull request number
            diff: PR diff to apply
            
        Returns:
            Dictionary with sandbox execution results:
                {
                    "status": "success" | "error",
                    "tests_run": int,
                    "tests_passed": int,
                    "tests_failed": int,
                    "errors": List[Dict],
                    "execution_time": float
                }
                
        Example:
            result = await processor._run_in_sandbox(
                "owner/repo",
                123,
                diff_string
            )
            # Returns: {
            #     "status": "success",
            #     "tests_run": 42,
            #     "tests_passed": 40,
            #     "tests_failed": 2,
            #     "errors": [
            #         {
            #             "error_type": "AssertionError",
            #             "message": "Expected 5 but got 4",
            #             "file": "tests/test_math.py",
            #             "line": 15,
            #             "stack_trace": "..."
            #         }
            #     ],
            #     "execution_time": 12.5
            # }
        """
        # Placeholder implementation
        logger.debug("Sandbox runner integration not yet implemented")
        return {
            "status": "not_implemented",
            "message": "Sandbox execution not yet available"
        }
