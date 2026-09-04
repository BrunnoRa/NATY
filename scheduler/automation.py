from dataclasses import dataclass


@dataclass(slots=True)
class AutomationRule:
    name: str
    trigger_type: str
    trigger_value: str
    action_type: str
    enabled: bool = True

    SAFE_ACTIONS = {"daily_summary", "notify_overdue", "notify_reminder"}

    def validate(self) -> bool:
        return self.trigger_type in {"time", "task_due", "reminder_due"} and self.action_type in self.SAFE_ACTIONS
