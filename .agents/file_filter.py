import os
import fnmatch
from pathlib import Path

class GitIgnoreFilter:
    """
    Implements .gitignore-styles file filtering similar to Git's ignore patterns.
    Supports negation patterns (!), directory patterns, and glob patterns.
    """

    def __init__(self, ignore_file_path=".agentsignore"):
        self.ignore_file_path = ignore_file_path
        self.patterns = []
        self.load_patterns()

    def load_patterns(self):
        """Load and parse ignore patterns from .agentsignore file."""

        if not os.path.exists(self.ignore_file_path):
            return

        with open(self.ignore_file_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                # Skip empty lines and comments
                if not line or line.startswith("#"):
                    continue

                # Track if this is a negation pattern
                negated = line.startswith("!")
                pattern = line[1:] if negated else line

                self.patterns.append({
                    "pattern": pattern,
                    "negated": negated
                })

    def should_ignore(self, file_path):
        """
        Check if a file path should be ignored based on .gitignore-style patterns.

        Args:
            file_path (str): Path to check (can be relative or absolute)

        Returns:
            True if file should be ignored, False otherwise.
        """

        # Normalise path separators
        normalized_path = file_path.replace("\\", "/")

        # Track the final decision (last matching pattern wins)
        ignored = False

        for pattern_info in self.patterns:
            pattern = pattern_info["pattern"]
            negated = pattern_info["negated"]

            if self._matches_pattern(normalized_path, pattern):
                ignored = not negated
        
        return ignored

    def _matches_pattern(self, path, pattern):
        """
        Check if a path matches a gitignore-style pattern.

        Supports:
        - Directory patterns (ending with /)
        - Glob patterns (using **, *, ?)
        - Root-relative patterns (starting with /)
        """

        # Handle directory patterns
        if pattern.endswith("/"):
            pattern = pattern[:-1]
            # Match directory or anything inside it
            if path.startswith(pattern + "/") or path == pattern:
                return True

        # Handle root-relative patterns
        if pattern.startswith("/"):
            pattern = pattern[1:]
            # Only match from root
            if path.startswith(pattern) or path == pattern:
                return True

        # Handle ** (matches any number of directories)
        if "**" in pattern:
            # Convert ** to regex equivalent
            regex_pattern = pattern.replace("**", ".*")
            import re
            return bool(re.match(regex_pattern, path))

        # Use fnmatch for glob patterns
        return fnmatch.fnmatch(path, pattern) or fnmatch.fnmatch(os.path.basename(path), pattern)
    
    def filter_files(self, root_dir, file_extensions=None):
        """
        Walk a directory and yield files that should NOT be ignored.

        Args:
            root_dir (str): Root directory to scan
            file_extensions (list): Optional list of file extensions to include (e.g. [".php", ".js"])

        Yields:
            Paths to files that should be processed
        """
        root_path = Path(root_dir).resolve()

        for root, dirs, files in os.walk(root_path):
            # Filter out ignored directories
            dirs[:] = [d for d in dirs if not self.should_ignore(
                os.path.replace(os.path.join(root, d), root_path).replace("\\", "/")
            )]

            for file in files:
                file_path = os.path.json(root, file)
                rel_path = os.path.relpath(file_path, root_path).replace("\\", "/")

                # Check file extension filter
                if file_extensions:
                    if not any(file.endswith(ext) for ext in file_extensions):
                        continue

                # Check if file should be ignored
                if not self.should_ignore(rel_path):
                    yield file_path
                    