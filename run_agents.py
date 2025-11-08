import os
import sys

from pathlib import Path
from dotenv import load_dotenv

# Add .agents directory to Python path
sys.path.insert(0, str(Path(__file__).parent / ".agents"))

from static_code_qa import StaticCodeQAAgent
from refactor_agent import RefactorAgent
from summary_agent import SummaryAgent

load_dotenv()

ignored = []
if os.path.exists(".agentsignore"):
    with open(".agentsignore", "r") as f:
        ignored = [line.strip() for line in f.readlines() if line.strip()]

# Instantiate agents
qa_agent = StaticCodeQAAgent(ignored_files=ignored)
refactor_agent = RefactorAgent()
summary_agent = SummaryAgent()

# Run static QA
qa_issues = qa_agent.scan_php_files(".")

# Run refactor suggestions
refactor_suggestions = refactor_agent.propose_refactors(qa_issues)

# Compile summary report
report = summary_agent.compile_report(qa_issues, refactor_suggestions)

# Save reports to file
os.makedirs("reports", exist_ok=True)
with open("reports/qa_report.md", "w", encoding="utf-8") as f:
    f.write(report)

print("QA report saved to reports/qa_report.md")
