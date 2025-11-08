import os
import json
import re
from pathlib import Path

from crewai import Agent, Task, Crew
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()

MODEL = os.getenv("MODEL", "gpt-oss:20b")
API_BASE = os.getenv("OPENAI_API_BASE", "http://localhost:11434/v1")


class RefactorAgent:
    """
    Refactor agent that suggests code consolidation, standardisation, and improvements.
    """
    
    def __init__(self):
        self.llm = ChatOpenAI(
            model=MODEL,
            base_url=API_BASE,
            temperature=0.2,
        )
        
        self.agent = Agent(
            role="PHP Refactoring Specialist",
            goal="Identify code consolidation opportunities and suggest refactoring improvements",
            backstory="""You are an expert PHP refactoring specialist with deep knowledge of WordPress/WooCommerce patterns.
            You identify duplicate code, consolidation opportunities (like rb_get_layout_config pattern),
            template structure inconsistencies, and suggest ways to improve maintainability and consistency.""",
            llm=self.llm,
            verbose=True,
        )
    
    def propose_refactors(self, qa_issues, codebase_path="."):
        """
        Analyse QA issues and codebase to propose refactoring suggestions.

        Args:
            qa_issues (list): List of issues from StaticCodeQAAgent
            codebase_path (str): Path to codebase root

        Returns:
            list: List of refactor suggestions with severity, file, line, suggestion, reasoning, and examples
        """
        # Group issues by type for better analysis
        consolidation_issues = [i for i in qa_issues if "consolidat" in i.get("issue", "").lower()]
        duplicate_code_issues = [i for i in qa_issues if "duplicate" in i.get("issue", "").lower()]
        
        prompt = f"""You are analysing a WordPress/WooCommerce codebase for refactoring opportunities.

**Key Patterns to Look For:**

1. **Code Consolidation (HIGH PRIORITY):**
   - Repeated configuration arrays that should use `rb_get_layout_config()`
   - Example BAD: Inline config arrays in multiple files
   - Example GOOD: `rb_get_layout_post_ids( rb_get_layout_config( 'posts' ) )`
   - Look for similar array structures repeated across files

2. **Duplicate Functions/Templates:**
   - Similar template code that could be consolidated
   - Repeated logic that could be extracted to helper functions
   - Inconsistent implementations of the same feature

3. **Template Structure Consistency:**
   - Inconsistent use of `rb_get_component_block()` vs direct includes
   - Inconsistent class naming patterns
   - Inconsistent early return patterns

4. **Function Naming:**
   - Functions missing `rb_` prefix
   - Inconsistent naming conventions

5. **ACF Pattern Standardisation:**
   - Inconsistent ACF field access patterns
   - Opportunities to create reusable ACF field helpers

**QA Issues Found:**
{json.dumps(qa_issues[:50], indent=2)}  # Limit to first 50 for context

Analyse the codebase and provide refactoring suggestions. Return JSON array:

[
  {{
    "severity": "error" | "warning" | "info",
    "file": "file path or 'multiple'",
    "line": <line_number or null>,
    "suggestion": "Clear refactoring suggestion",
    "reasoning": "Why this refactoring improves the codebase",
    "example_before": "Code example before refactoring",
    "example_after": "Code example after refactoring",
    "affected_files": ["list", "of", "files", "if", "applicable"]
  }}
]

Focus on high-impact refactorings that improve maintainability and consistency."""

        try:
            task = Task(
                description=prompt,
                agent=self.agent,
            )
            
            crew = Crew(
                agents=[self.agent],
                tasks=[task],
                verbose=True,
            )
            
            result = crew.kickoff()
            response_text = str(result)
            
            # Extract JSON from response
            json_match = re.search(r'\[.*\]', response_text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(0))
            else:
                return json.loads(response_text)
        
        except json.JSONDecodeError as e:
            print(f"Warning: Could not parse refactor JSON: {e}")
            return []
        except Exception as e:
            print(f"Error generating refactor suggestions: {e}")
            return []
