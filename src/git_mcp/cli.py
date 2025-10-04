import sys
import subprocess
import tempfile
import os
from .core import GitStatus
from .formatter import CommitMessageFormatter

def edit_message(message: str) -> str:
    """
    Open the message in a text editor for modification
    """
    with tempfile.NamedTemporaryFile(mode='w+', suffix='.txt', delete=False) as tf:
        tf.write(message)
        tf.flush()
        
        # Use git's configured editor, fallback to system default
        try:
            editor = subprocess.check_output(['git', 'config', 'core.editor'], 
                                          text=True).strip()
        except subprocess.CalledProcessError:
            editor = os.environ.get('EDITOR', 'notepad' if os.name == 'nt' else 'nano')
        
        try:
            subprocess.run([editor, tf.name], check=True)
            with open(tf.name, 'r') as f:
                edited_message = f.read().strip()
        except subprocess.CalledProcessError:
            print(f"Warning: Editor '{editor}' failed, keeping original message")
            edited_message = message
    
    os.unlink(tf.name)
    return edited_message

def main():
    git_status = GitStatus()
    
    try:
        changes = git_status.get_changed_files()
        if not changes:
            print("No changes to commit!")
            return
            
        categories = git_status.categorize_changes()
        message = git_status.generate_commit_message(categories)
        
        if len(sys.argv) > 1 and sys.argv[1] == '--edit':
            message = edit_message(message)
            
        subprocess.run(['git', 'commit', '-m', message])
        print(f"Committed with message:\n{message}")
        
    except subprocess.CalledProcessError:
        print("Error: Not a git repository or git command failed")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()