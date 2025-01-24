from typing import List, Optional
from datetime import datetime
class JiraTask:
    def __init__(
        self,
        id: str,
        summary: str,
        description: Optional[str],
        status: str,
        priority: Optional[str],
        assignees: List[str],
        created: str,
        updated: Optional[str],
        due_date: Optional[str],
        labels: Optional[List[str]] = None,
    ):
        self.id = id
        self.summary = summary
        self.description = description
        self.status = status
        self.priority = priority
        self.assignees = assignees
        self.created = created
        self.updated = updated
        self.due_date = due_date
        self.labels = labels or []

    def __repr__(self):
        return f"<JiraTask id={self.id} summary={self.summary}>"
    def to_dict(self):
        """
        Chuyển đổi đối tượng JiraTask thành dictionary.
        """
        return {
            "id": self.id,
            "summary": self.summary,
            "description": self.description,
            "status": self.status,
            "priority": self.priority,
            "assignees": self.assignees,
            "created": self.created,
            "updated": self.updated,
            "due_date": self.due_date,
            "labels": self.labels,
        }
