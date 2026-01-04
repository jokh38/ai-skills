"""Tool management for LLM API - file operation tools and execution framework"""
from pathlib import Path
from typing import Dict, Any, List, Callable


class ToolManager:
    """Manages tool definitions and execution for file operations"""

    def __init__(self):
        self._tools: Dict[str, Callable] = {}
        self._initialize_file_tools()

    def _initialize_file_tools(self):
        """Initialize file operation tools."""
        self._tools = {
            "create_file": self._tool_create_file,
            "edit_file": self._tool_edit_file,
            "remove_file": self._tool_remove_file,
            "read_file": self._tool_read_file,
        }

    def get_file_tools_schema(self) -> List[Dict[str, Any]]:
        """Get OpenAI-compatible tool schema for file operations."""
        return [
            {
                "type": "function",
                "function": {
                    "name": "create_file",
                    "description": "Create a new file with the specified content. Returns success message or error.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "filepath": {
                                "type": "string",
                                "description": "Path where the file should be created (relative or absolute)"
                            },
                            "content": {
                                "type": "string",
                                "description": "Content to write to the file"
                            }
                        },
                        "required": ["filepath", "content"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "edit_file",
                    "description": "Edit an existing file by replacing old content with new content. Returns success message or error.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "filepath": {
                                "type": "string",
                                "description": "Path to the file to edit"
                            },
                            "old_content": {
                                "type": "string",
                                "description": "Content to find and replace (must match exactly)"
                            },
                            "new_content": {
                                "type": "string",
                                "description": "New content to replace the old content with"
                            }
                        },
                        "required": ["filepath", "old_content", "new_content"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "remove_file",
                    "description": "Delete a file from the filesystem. Returns success message or error.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "filepath": {
                                "type": "string",
                                "description": "Path to the file to remove"
                            }
                        },
                        "required": ["filepath"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "read_file",
                    "description": "Read the contents of a file. Returns file content or error.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "filepath": {
                                "type": "string",
                                "description": "Path to the file to read"
                            }
                        },
                        "required": ["filepath"]
                    }
                }
            }
        ]

    def _tool_create_file(self, filepath: str, content: str) -> str:
        """Tool function to create a file."""
        try:
            file_path = Path(filepath)
            # Create parent directories if they don't exist
            file_path.parent.mkdir(parents=True, exist_ok=True)
            # Write content to file
            file_path.write_text(content)
            return f"Successfully created file: {filepath}"
        except Exception as e:
            return f"Error creating file {filepath}: {str(e)}"

    def _tool_edit_file(self, filepath: str, old_content: str, new_content: str) -> str:
        """Tool function to edit a file."""
        try:
            file_path = Path(filepath)
            if not file_path.exists():
                return f"Error: File {filepath} does not exist"

            current_content = file_path.read_text()
            if old_content not in current_content:
                return f"Error: Old content not found in {filepath}"

            updated_content = current_content.replace(old_content, new_content)
            file_path.write_text(updated_content)
            return f"Successfully edited file: {filepath}"
        except Exception as e:
            return f"Error editing file {filepath}: {str(e)}"

    def _tool_remove_file(self, filepath: str) -> str:
        """Tool function to remove a file."""
        try:
            file_path = Path(filepath)
            if not file_path.exists():
                return f"Error: File {filepath} does not exist"

            file_path.unlink()
            return f"Successfully removed file: {filepath}"
        except Exception as e:
            return f"Error removing file {filepath}: {str(e)}"

    def _tool_read_file(self, filepath: str) -> str:
        """Tool function to read a file."""
        try:
            file_path = Path(filepath)
            if not file_path.exists():
                return f"Error: File {filepath} does not exist"

            content = file_path.read_text()
            return f"Content of {filepath}:\n{content}"
        except Exception as e:
            return f"Error reading file {filepath}: {str(e)}"

    def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        """Execute a tool by name with given arguments."""
        if tool_name not in self._tools:
            return f"Error: Unknown tool '{tool_name}'"

        tool_func = self._tools[tool_name]
        try:
            return tool_func(**arguments)
        except Exception as e:
            return f"Error executing tool {tool_name}: {str(e)}"
