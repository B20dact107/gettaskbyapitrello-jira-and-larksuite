from enum import Enum
from typing import Optional, Any
from dataclasses import dataclass, field


@dataclass
class ResponseBody:
    result: Any
    status: int
    message: Optional[str] = None
    code: Optional[int] = None

    def __init__(self, result: Any, status: 'Status', message: Optional[str] = None, code: Optional['Code'] = None):
        self.result = result
        self.status = status.value
        self.message = message if message else (code.message if code else None)
        self.code = code.value if code else None
    def to_dict(self):
        return {
            "result": self.result,
            "status": self.status,
            "message": self.message,
            "code": self.code
        }


class Status(Enum):
    SUCCESS = 1
    FAILED = 0

    def __str__(self):
        return self.name

    @property
    def value(self):
        return self._value_


class Code(Enum):
    SUCCESS = (200, "Successful")
    CLIENT_ERROR = (400, "Client error")
    UNAUTHORIZED_REQUEST = (403, "Unauthorized request")
    NOT_FOUND = (404, "Not found")
    TOKEN_NOT_REGISTER = (3001, "Token not register")
    INVALID_REQUEST_FORMAT = (4010, "Invalid request format")
    INTERNAL_ERROR = (500, "Internal server error")

    def __init__(self, value, message):
        self._value_ = value
        self._message = message

    @property
    def value(self):
        return self._value_

    @property
    def message(self):
        return self._message
