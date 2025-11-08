import json
from math import e

from crewai import Agent
from datetime import datetime

class SummaryAgent(Agent):
    def __init__(self, name="SummaryAgent", model="gpt-oss:20b", proposal_db="proposals.json"):
        super().__init__(name=name, model=model, role="Compile QA report")
        self.proposal_db = proposal_db
        
        # Load previous proposals
        try:
            with open(self.proposal_db, "r") as f:
                self.proposals = json.load(f)
        except FileNotFoundError:
            self.proposals = {"proposals": []}

    def compile_report(self, qa_issues, refactor_suggestions):
        prompt = f"""
        You are a summary agent. Compile a Markdown report using the following QA issues: {json.dumps(qa_issues, indent=2)}
        Refactor suggestions: {json.dumps(refactor_suggestions, indent=2)}
        Include severity, recommendation, and references.
        """
        markdown = self.run(prompt)

        # Log proposals to avoid repeating suggestions
        self._log_proposals(refactor_suggestions)
        return markdown

    def _log_proposals(self, refactor_suggestions):
        for suggestion in refactor_suggestions:
            entry = {
                "file": suggestion["file"],
                "line": suggestion["line"],
                "suggestion": suggestion["suggestion"],
                "timestamp": datetime.now().isoformat(),
                "status": "pending"
            }

            if entry not in self.proposals["proposals"]:
                self.proposals["proposals"].append(entry)

        with open(self.proposal_db, "w") as f:
            json.dump(self.proposals, f, indent=2)
