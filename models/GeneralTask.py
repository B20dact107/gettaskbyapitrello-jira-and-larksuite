from typing import List, Optional
from datetime import datetime

from models.LarksuiteTask import LarksuiteTask
from JiraTask import JiraTask
from models.TrelloTask import TrelloTask

class GeneralTask:
    def __init__(
        self,
        task_id: str,
        title: str,
        description: Optional[str],
        status: str,
        priority: Optional[str],
        assignees: List[str],
        created_at: datetime,
        updated_at: Optional[datetime],
        due_date: Optional[datetime],
        labels: Optional[List[str]] = None,
        source: str = "unknown", 
        additional_data: Optional[dict] = None  # Để lưu các thông tin mở rộng
    ):
        self.task_id = task_id
        self.title = title
        self.description = description
        self.status = status
        self.priority = priority
        self.assignees = assignees
        self.created_at = created_at
        self.updated_at = updated_at
        self.due_date = due_date
        self.labels = labels or []
        self.source = source
        self.additional_data = additional_data or {}

    def __repr__(self):
        return f"<GeneralTask id={self.task_id} title={self.title} source={self.source}>"


# # Chuyển đổi từ Trello sang GeneralTask
# def trello_to_general(task: TrelloTask) -> GeneralTask:
#     return GeneralTask(
#         task_id=task.id,
#         title=task.name,
#         description=task.desc,
#         status=task.list_name,
#         priority=None,  
#         assignees=task.members,
#         created_at=datetime.strptime(task.created_at, "%Y-%m-%dT%H:%M:%S"),
#         updated_at=datetime.strptime(task.updated_at, "%Y-%m-%dT%H:%M:%S") if task.updated_at else None,
#         due_date=datetime.strptime(task.due_date, "%Y-%m-%dT%H:%M:%S") if task.due_date else None,
#         labels=task.labels,
#         source="Trello",
#     )


# # Chuyển đổi từ Jira sang GeneralTask
# def jira_to_general(task: JiraTask) -> GeneralTask:
#     return GeneralTask(
#         task_id=task.id,
#         title=task.summary,
#         description=task.description,
#         status=task.status,
#         priority=task.priority,
#         assignees=task.assignees,
#         created_at=datetime.strptime(task.created, "%Y-%m-%dT%H:%M:%S"),
#         updated_at=datetime.strptime(task.updated, "%Y-%m-%dT%H:%M:%S") if task.updated else None,
#         due_date=datetime.strptime(task.due_date, "%Y-%m-%dT%H:%M:%S") if task.due_date else None,
#         labels=task.labels,
#         source="Jira",
#     )


# def larksuite_to_general(task: LarksuiteTask) -> GeneralTask:
#     return GeneralTask(
#         task_id=task.task_id,
#         title=task.title,
#         description=task.description,
#         status=task.status,
#         priority=task.priority,
#         assignees=task.assignees,
#         created_at=datetime.strptime(task.created_date, "%Y-%m-%dT%H:%M:%S"),
#         updated_at=datetime.strptime(task.last_modified_date, "%Y-%m-%dT%H:%M:%S") if task.last_modified_date else None,
#         due_date=datetime.strptime(task.due_date, "%Y-%m-%dT%H:%M:%S") if task.due_date else None,
#         labels=task.tags,
#         source="Larksuite",
#     )