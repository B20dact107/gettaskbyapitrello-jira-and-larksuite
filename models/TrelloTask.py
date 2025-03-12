from typing import List, Optional
from datetime import datetime

# Class đại diện cho task từ Trello
class TrelloTask:
    def __init__(
        self,
        id: str,
        title: str,
        desc: Optional[str],
        list_name: str,
        members: List[str],
        created_at: str,
        updated_at: Optional[str],
        due_date: Optional[str],
        labels: Optional[List[str]] = None,
        extend: Optional[dict] = None,
    ):
        self.id = id
        self.title = title
        self.desc = desc
        self.list_name = list_name
        self.members = members
        self.created_at = created_at
        self.updated_at = updated_at
        self.due_date = due_date
        self.labels = labels or []
        self.extend = extend or {}

    def __repr__(self):
        return f"<TrelloTask id={self.id} name={self.title}>"

