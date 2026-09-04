from core.models import ToolResult


class ResponseFormatter:
    def format(self, result: ToolResult) -> str:
        text = result.message.strip()
        if result.sources:
            text += "\n\nFontes:\n" + "\n".join(f"- {s['title']}: {s['url']}" for s in result.sources)
        return text
