import json
import os
from datetime import datetime
from pathlib import Path

from crewai import Agent, Task, Crew
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()

MODEL = os.getenv("MODEL", "gpt-oss:20b")
API_BASE = os.getenv("OPENAI_API_BASE", "http://localhost:11434/v1")


class SummaryAgent:
    """
    Summary agent that compiles QA issues and refactor suggestions into a comprehensive report.
    """
    
    def __init__(self, proposal_db="proposals.json"):
        self.proposal_db = proposal_db
        self.llm = ChatOpenAI(
            model=MODEL,
            base_url=API_BASE,
            temperature=0.1,
        )
        
        self.agent = Agent(
            role="QA Report Compiler",
            goal="Compile comprehensive QA reports with severity, recommendations, and references",
            backstory="""You are an expert technical writer specialising in code quality reports.
            You compile QA findings into clear, actionable reports with proper severity classification,
            prioritised recommendations, and references to documentation.""",
            llm=self.llm,
            verbose=True,
        )
        
        # Load previous proposals
        self.proposals = self._load_proposals()
    
    def _load_proposals(self):
        """Load previous proposals from database."""
        if os.path.exists(self.proposal_db):
            try:
                with open(self.proposal_db, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {"proposals": []}
    
    def compile_report(self, qa_issues, refactor_suggestions):
        """
        Compile a comprehensive Markdown QA report.

        Args:
            qa_issues (list): List of QA issues from StaticCodeQAAgent
            refactor_suggestions (list): List of refactor suggestions from RefactorAgent

        Returns:
            str: Markdown formatted report string
        """
        # Filter out previously rejected proposals
        filtered_qa = self._filter_rejected_proposals(qa_issues)
        filtered_refactors = self._filter_rejected_proposals(refactor_suggestions)
        
        # Group issues by severity
        errors = [i for i in filtered_qa if i.get("severity") == "error"]
        warnings = [i for i in filtered_qa if i.get("severity") == "warning"]
        info = [i for i in filtered_qa if i.get("severity") == "info"]
        
        prompt = f"""Compile a comprehensive QA report in Markdown format.

**QA Issues Found:**
- Errors: {len(errors)}
- Warnings: {len(warnings)}
- Info: {len(info)}

**Refactor Suggestions:** {len(filtered_refactors)}

Create a well-structured Markdown report with:

1. **Executive Summary** - Overview of findings
2. **Critical Issues (Errors)** - Must-fix items with code examples
3. **Warnings** - Should-fix items
4. **Info** - Nice-to-have improvements
5. **Refactoring Opportunities** - Code consolidation and standardisation suggestions
6. **Recommendations** - Prioritised action items
7. **References** - Links to WordPress/WooCommerce documentation

Format the report professionally with proper headings, code blocks, and tables.
Include specific file paths, line numbers, and actionable fixes.

QA Issues:
{json.dumps(filtered_qa[:100], indent=2)}

Refactor Suggestions:
{json.dumps(filtered_refactors[:50], indent=2)}
"""

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
            markdown = str(result)
            
            # Log proposals
            self._log_proposals(qa_issues + refactor_suggestions)
            
            return markdown
        
        except Exception as e:
            print(f"Error compiling report: {e}")
            return self._fallback_report(qa_issues, refactor_suggestions)
    
    def _filter_rejected_proposals(self, items):
        """Filter out items that were previously rejected."""
        rejected_ids = {
            f"{item.get('file', '')}:{item.get('line', '')}"
            for item in self.proposals.get("proposals", [])
            if item.get("status") == "rejected"
        }
        
        return [
            item for item in items
            if f"{item.get('file', '')}:{item.get('line', '')}" not in rejected_ids
        ]
    
    def _log_proposals(self, items):
        """Log proposals to avoid repeating suggestions."""
        for item in items:
            proposal_id = f"{item.get('file', 'unknown')}:{item.get('line', 'unknown')}"
            
            # Check if already logged
            existing = next(
                (p for p in self.proposals["proposals"] if p.get("id") == proposal_id),
                None
            )
            
            if not existing:
                entry = {
                    "id": proposal_id,
                    "file": item.get("file", ""),
                    "line": item.get("line"),
                    "issue": item.get("issue") or item.get("suggestion", ""),
                    "severity": item.get("severity", "info"),
                    "timestamp": datetime.now().isoformat(),
                    "status": "pending"
                }
                self.proposals["proposals"].append(entry)
        
        # Save to file
        os.makedirs(os.path.dirname(self.proposal_db) if os.path.dirname(self.proposal_db) else ".", exist_ok=True)
        with open(self.proposal_db, "w", encoding="utf-8") as f:
            json.dump(self.proposals, f, indent=2)
    
    def _fallback_report(self, qa_issues, refactor_suggestions):
        """Generate a basic report if LLM fails."""
        report = "# QA Report\n\n"
        report += f"Generated: {datetime.now().isoformat()}\n\n"
        report += f"## Summary\n\n"
        report += f"- Total Issues: {len(qa_issues)}\n"
        report += f"- Refactor Suggestions: {len(refactor_suggestions)}\n\n"
        report += "## Issues\n\n"
        
        for issue in qa_issues[:20]:  # Limit for fallback
            report += f"### {issue.get('file', 'Unknown')}:{issue.get('line', '?')}\n"
            report += f"**{issue.get('severity', 'info').upper()}**: {issue.get('issue', '')}\n\n"
        
        return report
