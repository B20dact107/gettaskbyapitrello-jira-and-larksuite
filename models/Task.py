from datetime import datetime
from dateutil import parser as date_parser

from typing import List, Optional, Dict, Any
from enum import Enum

from models.JiraTask import JiraTask
from models.LarksuiteTask import LarksuiteTask
from models.TrelloTask import TrelloTask

class TaskStatus(str, Enum):
    TODO = "to_do"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    PENDING = "pending"

class TaskPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

class Task:
    def __init__(
        self,
        task_id: str,
        title: str,
        source: str,  # "jira", "trello", "larksuite"
        status: TaskStatus,
        created_at: datetime,
        updated_at: Optional[datetime] = None,
        due_date: Optional[datetime] = None,
        description: Optional[str] = None,
        assignees: List[str] = [],
        priority: TaskPriority = TaskPriority.MEDIUM,
        metadata: Dict[str, Any] = {}  # Chứa dữ liệu đặc thù platform
    ):
        self.id = f"{source}:{task_id}"
        self.title = title
        self.source = source
        self.status = status
        self.created_at = created_at
        self.updated_at = updated_at
        self.due_date = due_date
        self.description = description
        self.assignees = assignees
        self.priority = priority
        self.metadata = metadata

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "source": self.source,
            "status": self.status.value,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "description": self.description,
            "assignees": self.assignees,
            "priority": self.priority.value,
            "metadata": self.metadata
        }

    @classmethod
    def from_jira(cls, jira_task: 'JiraTask'):
        project_info = {
        "_id": getattr(jira_task, "project_id", None),             # Ví dụ: jira_task.project_id
        "name": getattr(jira_task, "project_name", None),            # Ví dụ: jira_task.project_name
        "description": getattr(jira_task, "project_description", None),  # Ví dụ: jira_task.project_description
        "owner": getattr(jira_task, "project_owner", None),          # Ví dụ: jira_task.project_owner
        "members": getattr(jira_task, "project_members", [])         # Ví dụ: jira_task.project_members
        }
     
        return cls(
            task_id=jira_task.id,
            title=jira_task.summary,
            source="jira",
            status=TaskStatus(jira_task.status.lower().replace(" ", "_")),
            created_at = date_parser.parse(jira_task.created),
            updated_at = date_parser.parse(jira_task.updated) if jira_task.updated else None,
            due_date = date_parser.parse(jira_task.due_date) if jira_task.due_date else None,
            description=jira_task.description,
            assignees=jira_task.assignees,
            priority=TaskPriority(jira_task.priority.lower() if jira_task.priority else "medium"),
            metadata={
                "labels": jira_task.labels,
                "project_info": project_info
            }
        )
    
    @classmethod
    def from_larksuite(cls, larksuite_task: 'LarksuiteTask'):
        status = TaskStatus.DONE if larksuite_task.completed_at != "0" else TaskStatus.PENDING
    
    # Xử lý thời gian
        created_at = datetime.fromtimestamp(int(larksuite_task.extra_data.get("created_at", 0))/1000)
        due_date = None
        if larksuite_task.due and "timestamp" in larksuite_task.due:
            due_date = datetime.fromtimestamp(int(larksuite_task.due["timestamp"])/1000)
    
        return cls(
            task_id=larksuite_task.task_id,
            title=larksuite_task.summary,
            source="larksuite",
            status=status,
            created_at=created_at,
            due_date=due_date,
            assignees=larksuite_task.members,
            metadata={
                "subtask_count": larksuite_task.subtask_count,
                "platform_data": larksuite_task.extra_data
            }
        )
       
    @classmethod
    def from_trello(cls, trello_task: 'TrelloTask'):
        status_mapping = {
            "To Do": TaskStatus.TODO,
            "In Progress": TaskStatus.IN_PROGRESS,
            "Done": TaskStatus.DONE
        }
        status = status_mapping.get(trello_task.list_name, TaskStatus.PENDING)
        
        created_at = date_parser.parse(trello_task.created_at) if trello_task.created_at else None
        updated_at = date_parser.parse(trello_task.updated_at) if trello_task.updated_at else None
        due_date = date_parser.parse(trello_task.due_date) if trello_task.due_date else None
        
        return cls(
            task_id=trello_task.id,
            title=trello_task.name,
            source="trello",
            status=status,
            created_at=created_at,
            updated_at=updated_at,
            due_date=due_date,
            description=trello_task.desc,
            assignees=trello_task.members,
            priority=TaskPriority.MEDIUM,
            metadata={
                "board": {
                    "id": trello_task.board_id,
                    "name": trello_task.board_name,
                    "url": trello_task.board_url
                },
               "list": {
                    "id": trello_task.list_id,
                    "name": trello_task.list_name
                },
                "labels": trello_task.labels,
                "card_url": trello_task.card_url,
                "comments": trello_task.comments
            }
        )