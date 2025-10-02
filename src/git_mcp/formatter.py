class CommitMessageFormatter:
    def __init__(self, template_style="default"):
        self.template_style = template_style

    def format_message(self, categories: dict) -> str:
        """
        Format the commit message based on categorized changes
        """
        message_parts = []
        
        if categories['added']:
            message_parts.append("Add: " + ", ".join(categories['added']))
        if categories['modified']:
            message_parts.append("Update: " + ", ".join(categories['modified']))
        if categories['deleted']:
            message_parts.append("Remove: " + ", ".join(categories['deleted']))
            
        return "\n".join(message_parts)