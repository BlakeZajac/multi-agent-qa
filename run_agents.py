import os
import sys
import json

from pathlib import Path
from dotenv import load_dotenv

# Add .agents directory to Python path
sys.path.insert(0, str(Path(__file__).parent / ".agents"))

from static_code_qa import StaticCodeQAAgent
from refactor_agent import RefactorAgent
from summary_agent import SummaryAgent

load_dotenv()

def main():
    # Initialize agents
    qa_agent = StaticCodeQAAgent(ignore_file=".agentsignore")
    refactor_agent = RefactorAgent()
    summary_agent = SummaryAgent()
    
    print("Starting QA scan...")
    
    # Run static QA
    qa_issues = qa_agent.scan_php_files(".")
    
    print(f"\nFound {len(qa_issues)} QA issues")
    
    # Run refactor suggestions
    print("\nAnalyzing refactoring opportunities...")
    refactor_suggestions = refactor_agent.propose_refactors(qa_issues)
    
    print(f"Found {len(refactor_suggestions)} refactoring suggestions")
    
    # Compile summary report
    print("\nCompiling report...")
    report = summary_agent.compile_report(qa_issues, refactor_suggestions)
    
    # Save reports
    os.makedirs("reports", exist_ok=True)
    
    # Save Markdown report
    with open("reports/qa_report.md", "w", encoding="utf-8") as f:
        f.write(report)
    
    # Save JSON for programmatic access
    with open("reports/qa_issues.json", "w", encoding="utf-8") as f:
        json.dump(qa_issues, f, indent=2)
    
    with open("reports/refactor_suggestions.json", "w", encoding="utf-8") as f:
        json.dump(refactor_suggestions, f, indent=2)
    
    print("\n✅ QA report saved to reports/qa_report.md")
    print("✅ Issues saved to reports/qa_issues.json")
    print("✅ Refactor suggestions saved to reports/refactor_suggestions.json")

if __name__ == "__main__":
    main()
