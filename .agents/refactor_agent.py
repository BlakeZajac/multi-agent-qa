import json

from crewai import Agent

class RefactorAgent(Agent):
    def __init__(self, name="RefactorAgent", model="gpt-oss:20b"):
        super().__init__(name=name, model=model, role="Refactor suggestion agent")

    def propose_refactors(self, qa_issues):
        prompt = f"""
        You are a PHP refactor agent. Given the following QA results:
        {json.dumps(qa_issues, indent=2)}
        Suggest:
        1. Consolidation of repeated code or template logic
        2. Template unification opportunities
        3. Any general refactor plans for cleaner, more maintainable code.
        Return JSON in this format:
        [
            {{
                "file": "<file_path>",
                "line": <line_number>,
                "refactor": <refactor proposal>
            }}
        ]
        """

        response = self.run(prompt)

        try:
            return json.loads(response)
        except json.JSONDecodeError:
            print("Warning: could not parse refactor JSON")
            return []