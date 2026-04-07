import json
from abc import ABC, abstractmethod
from typing import Any
from pydantic import BaseModel
from langchain.tools import BaseTool

class AgentToolResult(BaseModel):
    success: bool
    data: Any | None = None
    error: str | None = None

    def to_str(self) -> str:
        return json.dumps(self.model_dump())

class BaseAgentTool(BaseTool, ABC):
    @abstractmethod
    def execute(self, **kwargs: Any) -> AgentToolResult:
        """Abstract method for tool execution."""
        pass

    def _run(self, *args: Any, **kwargs: Any) -> str:
        """LangChain method for tool execution."""
        try:
            # Handle both positional and keyword arguments
            if args and not kwargs:
                # If single string argument is passed, try to parse as JSON or use directly
                if len(args) == 1 and isinstance(args[0], str):
                    try:
                        kwargs = json.loads(args[0])
                    except json.JSONDecodeError:
                        # Fallback for simple tools with one argument
                        kwargs = {"input": args[0]}
                else:
                    # Map positional args to kwargs if needed, or just pass as is
                    kwargs = {"args": args}
            
            result = self.execute(**kwargs)
            return result.to_str()
        except Exception as e:
            return AgentToolResult(success=False, error=str(e)).to_str()

    async def _arun(self, *args: Any, **kwargs: Any) -> str:
        """Asynchronous LangChain method for tool execution."""
        return self._run(*args, **kwargs)
