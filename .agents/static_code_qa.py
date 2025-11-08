import os
import json
import re
from pathlib import Path
from crewai import Agent, Task, Crew
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from file_filter import GitIgnoreFilter

load_dotenv()

MODEL = os.getenv("MODEL", "gpt-oss:20b")
API_BASE = os.getenv("OPENAI_API_BASE", "http://localhost:11434/v1")

class StaticCodeQAAgent:
    """
    Static code QA agent that analyses PHP files for WordPress/WooCommerce best practices.
    Detects: unguarded array keys, missing sanitisation, missing rb_prefixes, and more.
    """

    def __init__(self, ignored_files=None, ignore_file=".agentsignore"):
        self.file_filter = GitIgnoreFilter(ignore_file)
        self.llm = ChatOpenAI(
            model=MODEL,
            base_url=API_BASE,
            temperature=0.1,
        )
        self.agent = Agent(
            role="PHP Code Quality Analyst",
            goal="Identify PHP code quality issues in WordPress/WooCommerce codebases following best practices",
            backstory="""You are an expert PHP code reviewer specialising in WordPress and WooCommerce development.
            You have deep knowledge of WordPress coding standards, security best practices, and the rb_ function prefix convention.
            You analyse code for unguarded array access, missing sanitisation/escaping, code consolidation opportunities,
            and adherence to WordPress/WooCommerce coding standards.""",
            llm=self.llm,
            verbose=True,
        )
    
    def scan_php_files(self, folder):
        """
        Scan PHP files in the given folder and return QA issues.

        Args:
            folder (str): Root folder to scan

        Return:
            List of issue dictionaries with severity, file, line, issue, fix, and references
        """
        issues = []
        php_files = list(self.file_filter.filter_files(folder, [".php"]))

        print(f"Scanning {len(php_files)} PHP files...")

        for file_path in php_files:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()

                # Analyse with LLM
                llm_issues = self._analyse_php_content(file_path, content)
                if llm_issues:
                    issues.extend(llm_issues)

            except Exception as e:
                print(f"Error scanning {file_path}: {e}")
                continue

        return issues

    def _analyse_php_content(self, file_path, content):
        """Use LLM to analyze PHP content for quality issues."""
        prompt = f"""You are analyzing PHP code for a WordPress/WooCommerce project. 
The codebase follows these patterns from the "after-qa" version:

**Array Access Patterns:**
- Always use isset() checks before accessing array keys: `if ( ! isset( $link['url'] ) || ! isset( $link['title'] ) ) continue;`
- Use null coalescing operator for defaults: `$file_id = $file['file'] ?? '';`
- Check array keys before use: `$link = isset( $link['url'] ) ? $link : array( 'url' => '...', 'title' => '...' );`

**Sanitisation/Escaping:**
- Always escape output: `esc_html()`, `esc_url()`, `esc_attr()`, `wp_kses()`
- Use appropriate escaping function for context
- Example: `<?php echo esc_html( $file_label ); ?>`
- Example: `href="<?php echo esc_url( $link['url'] ); ?>"`

**Function Naming:**
- All custom functions MUST be prefixed with `rb_` (e.g., `rb_get_component_block()`, `rb_get_layout_config()`)
- Functions without `rb_` prefix are violations

**Code Consolidation:**
- Repeated configuration arrays should use helper functions like `rb_get_layout_config()`
- Example: Instead of inline config arrays, use: `rb_get_layout_post_ids( rb_get_layout_config( 'posts' ) )`

**ACF Field Access:**
- Use `get_sub_field()`, `get_field()`, `the_sub_field()`, `the_field()` properly
- Always check if fields exist before use
- Use `have_rows()` before `while ( have_rows() )` loops

**Template Structure:**
- Early returns: `if ( empty( $items ) ) return;`
- Consistent class naming and structure
- Proper use of `rb_get_component_block()` for reusable components

**WordPress/WooCommerce Standards:**
- Follow WordPress PHP Coding Standards
- Use WordPress functions instead of reinventing
- Proper nonce verification for forms
- Use wpdb->prepare() for database queries

Analyse the following PHP code in {file_path} and identify ALL issues:

```php
{content}
```

Return a JSON array of issues. Each issue must have:
- "severity": "error" | "warning" | "info"
- "file": "{file_path}"
- "line": <line_number>
- "issue": "Clear description of the problem"
- "fix": "Specific code fix or suggestion with reasoning"
- "references": ["URL or reference to WordPress/WooCommerce documentation"]

Only return valid JSON. If no issues found, return empty array [].

Example format:
[
  {{
    "severity": "error",
    "file": "src/components/layout-example/template.php",
    "line": 45,
    "issue": "Accessing array key 'url' without isset() check",
    "fix": "Add isset() check: if ( ! isset( $link['url'] ) || ! isset( $link['title'] ) ) continue;",
    "references": ["https://developer.wordpress.org/coding-standards/wordpress-coding-standards/php/"]
  }}
]
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
            
            # Extract JSON from response
            response_text = str(result)
            
            # Try to find JSON in the response
            json_match = re.search(r'\[.*\]', response_text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(0))
            else:
                # Try parsing the whole response
                return json.loads(response_text)
        
        except json.JSONDecodeError as e:
            print(f"Warning: Could not parse JSON for {file_path}: {e}")
            print(f"Response was: {response_text[:500]}")
            return []
        except Exception as e:
            print(f"Error analysing {file_path}: {e}")
            return []

