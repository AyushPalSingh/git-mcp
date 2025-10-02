from typing import List, Tuple
import subprocess
import google.generativeai as genai
import os
import readline
class GitStatus:
    def __init__(self):
        self.changes = []
        self.repo_root = self._get_repo_root()
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable is not set. Please set it before running the command.")
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.5-flash')

    def _get_repo_root(self) -> str:
        """Get the root directory of the git repository"""
        try:
            result = subprocess.run(
                ['git', 'rev-parse', '--show-toplevel'],
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError:
            return os.getcwd()

    def _get_file_content(self, file_path: str) -> str:
        """Get content of changed file"""
        try:
            full_path = os.path.join(self.repo_root, file_path)
            if os.path.exists(full_path):
                with open(full_path, 'r', encoding='utf-8') as f:
                    return f.read()
            return ''
        except Exception:
            return ''

    def _get_staged_diff(self, file_path: str) -> str:
        """Get git diff for staged changes"""
        try:
            # Get diff of staged changes
            result = subprocess.run(
                ['git', 'diff', '--cached', file_path],
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout
        except subprocess.CalledProcessError:
            return ''

    def _create_commit_prompt(self, categories: dict) -> str:
        changes = []
        for status, files in [
            ('Added', categories['added']),
            ('Modified', categories['modified']),
            ('Deleted', categories['deleted'])
        ]:
            if files:
                file_details = []
                for file in files:
                    if status == 'Modified':
                        diff = self._get_staged_diff(file)
                        if diff:
                            file_details.append(f"- {file}\nDiff:\n{diff}")
                    elif status == 'Added':
                        content = self._get_file_content(file)
                        if content:
                            file_details.append(f"- {file}\nNew content:\n{content[:500]}")
                    else:  # Deleted
                        file_details.append(f"- {file} (removed)")
                
                if file_details:
                    changes.append(f"{status} files:\n" + "\n".join(file_details))

        prompt = f"""Analyze these repository changes and create a meaningful commit message:

{'\n'.join(changes)}

You are a git commit message expert. Based on the changes:
1. What is the main purpose of these changes?
2. What functionality is being modified?
3. Are there any significant code changes?

IMPORTANT: Return ONLY the commit message without any analysis or explanation or promt : .
Format:
- First line: type(scope): brief description
- Optional second line: brief explanation if needed
- Max 72 chars per line
- Focus on the purpose of changes"""

        return prompt

    def get_changed_files(self) -> List[Tuple[str, str]]:
        """
        Get list of changed files from git status
        Returns: List of tuples (status, file_path)
        """
        # Get only staged changes using --cached flag
        result = subprocess.run(
            ['git', 'diff', '--cached', '--name-status'],
            capture_output=True,
            text=True,
            check=True
        )
        
        self.changes = [
            (line.split()[0].strip(), line.split()[1])
            for line in result.stdout.splitlines()
            if line.strip()
        ]
        return self.changes

    def categorize_changes(self) -> dict:
        """
        Categorize changes into added, modified, and deleted files
        """
        categories = {
            'added': [],
            'modified': [],
            'deleted': []
        }
        
        for status, file_path in self.changes:
            if status in ['A', '??']:
                categories['added'].append(file_path)
            elif status == 'M':
                categories['modified'].append(file_path)
            elif status == 'D':
                categories['deleted'].append(file_path)
                
        return categories

    def generate_commit_message(self, categories: dict) -> str:
        """Generate commit message using Gemini AI"""
        try:
            prompt = self._create_commit_prompt(categories)
            print("Analyzing changes...")
            response = self.model.generate_content(prompt)
            message = response.text.strip()
            
            # Validate the response
            if not message or message.lower().startswith('update:'):
                raise ValueError("Invalid AI response")
            
            # Show and allow editing of message in CLI
            print("\nGenerated commit message:")
            print("-" * 50)
            print(message)
            print("-" * 50)
            
            while True:
                choice = input("\nWould you like to edit this message? (y/n): ").lower()
                if choice == 'n':
                    return message
                elif choice == 'y':
                    # Pre-populate the input with the generated message
                    readline.set_startup_hook(lambda: readline.insert_text(message))
                    try:
                        new_message = input("Edit commit message: \n").strip()
                    finally:
                        readline.set_startup_hook()  # Reset the hook
                    
                    return new_message if new_message else message
                print("Please enter 'y' or 'n'")
                
        except Exception as e:
            print(f"Warning: Using fallback message ({str(e)})")
            return self._generate_fallback_message(categories)

    def _format_files(self, files: list) -> str:
        """Format file list with bullet points"""
        return '\n'.join(f"- {f}" for f in files)

    def _generate_fallback_message(self, categories: dict) -> str:
        """Generate basic message if Gemini fails"""
        if not any(categories.values()):
            print("No changes staged for commit. Please use 'git add' first.")
            return ""
            
        parts = []
        if categories['added']:
            parts.append(f"add: {len(categories['added'])} files")
        if categories['modified']:
            parts.append(f"update: {len(categories['modified'])} files")
        if categories['deleted']:
            parts.append(f"remove: {len(categories['deleted'])} files")
        return ' | '.join(parts)