import asyncio
import json
import os
import logging
import http.client
import requests
import sys
import uvicorn
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
import mcp.types as types

from mcp.server.lowlevel import Server
from mcp.server.sse import SseServerTransport
from dotenv import load_dotenv


from .ticktick_client import TickTickClient

# Get MCP logger
logger = logging.getLogger(__name__)

# Create Server
mcp = Server("ticktick")

@mcp.list_tools()
async def list_tools() -> list[types.Tool]:
    """List all available tools."""
    return [
        types.Tool(
            name="get_projects",
            description="Get all projects from TickTick.",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        types.Tool(
            name="get_project",
            description="Get details about a specific project.",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {
                        "type": "string",
                        "description": "ID of the project"
                    }
                },
                "required": ["project_id"]
            }
        ),
        types.Tool(
            name="get_project_tasks",
            description="Get all tasks in a specific project.",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {
                        "type": "string",
                        "description": "ID of the project"
                    }
                },
                "required": ["project_id"]
            }
        ),
        types.Tool(
            name="get_task",
            description="Get details about a specific task.",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {
                        "type": "string",
                        "description": "ID of the project"
                    },
                    "task_id": {
                        "type": "string",
                        "description": "ID of the task"
                    }
                },
                "required": ["project_id", "task_id"]
            }
        ),
        types.Tool(
            name="create_task",
            description="Create a new task in TickTick.",
            inputSchema={
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "Task title"
                    },
                    "project_id": {
                        "type": "string",
                        "description": "ID of the project to add the task to"
                    },
                    "content": {
                        "type": "string",
                        "description": "Task description/content (optional)"
                    },
                    "start_date": {
                        "type": "string",
                        "description": "Start date in ISO format YYYY-MM-DDThh:mm:ss+0000 (optional)"
                    },
                    "due_date": {
                        "type": "string",
                        "description": "Due date in ISO format YYYY-MM-DDThh:mm:ss+0000 (optional)"
                    },
                    "priority": {
                        "type": "integer",
                        "description": "Priority level (0: None, 1: Low, 3: Medium, 5: High) (optional)"
                    }
                },
                "required": ["title", "project_id"]
            }
        ),
        types.Tool(
            name="update_task",
            description="Update an existing task in TickTick.",
            inputSchema={
                "type": "object",
                "properties": {
                    "task_id": {
                        "type": "string",
                        "description": "ID of the task to update"
                    },
                    "project_id": {
                        "type": "string",
                        "description": "ID of the project the task belongs to"
                    },
                    "title": {
                        "type": "string",
                        "description": "New task title (optional)"
                    },
                    "content": {
                        "type": "string",
                        "description": "New task description/content (optional)"
                    },
                    "start_date": {
                        "type": "string",
                        "description": "New start date in ISO format YYYY-MM-DDThh:mm:ss+0000 (optional)"
                    },
                    "due_date": {
                        "type": "string",
                        "description": "New due date in ISO format YYYY-MM-DDThh:mm:ss+0000 (optional)"
                    },
                    "priority": {
                        "type": "integer",
                        "description": "New priority level (0: None, 1: Low, 3: Medium, 5: High) (optional)"
                    }
                },
                "required": ["task_id", "project_id"]
            }
        ),
        types.Tool(
            name="complete_task",
            description="Mark a task as complete.",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {
                        "type": "string",
                        "description": "ID of the project"
                    },
                    "task_id": {
                        "type": "string",
                        "description": "ID of the task"
                    }
                },
                "required": ["project_id", "task_id"]
            }
        ),
        types.Tool(
            name="delete_task",
            description="Delete a task.",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {
                        "type": "string",
                        "description": "ID of the project"
                    },
                    "task_id": {
                        "type": "string",
                        "description": "ID of the task"
                    }
                },
                "required": ["project_id", "task_id"]
            }
        ),
        types.Tool(
            name="create_project",
            description="Create a new project in TickTick.",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Project name"
                    },
                    "color": {
                        "type": "string",
                        "description": "Color code (hex format) (optional)"
                    },
                    "view_mode": {
                        "type": "string",
                        "description": "View mode - one of list, kanban, or timeline (optional)"
                    }
                },
                "required": ["name"]
            }
        ),
        types.Tool(
            name="delete_project",
            description="Delete a project.",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {
                        "type": "string",
                        "description": "ID of the project"
                    }
                },
                "required": ["project_id"]
            }
        )
    ]

# Create TickTick client
ticktick = None

def initialize_client():
    global ticktick
    try:
        # First, check if environment variables are directly available
        access_token = os.getenv("TICKTICK_ACCESS_TOKEN")
        
        # For token refresh, these are optional but useful
        refresh_token = os.getenv("TICKTICK_REFRESH_TOKEN")
        client_id = os.getenv("TICKTICK_CLIENT_ID")
        client_secret = os.getenv("TICKTICK_CLIENT_SECRET")
        
        # Use in-memory mode if access token is provided via environment
        in_memory_mode = False
        if access_token:
            in_memory_mode = True
        else:
            # Check if .env file exists with access token
            from pathlib import Path
            env_path = Path('.env')
            if not env_path.exists():
                logger.error("No .env file found and TICKTICK_ACCESS_TOKEN environment variable is not set. Please run 'uv run -m ticktick_mcp.cli auth' to set up authentication.")
                return False
            
            # Check if we have valid credentials in .env
            with open(env_path, 'r') as f:
                content = f.read()
                if 'TICKTICK_ACCESS_TOKEN' not in content:
                    logger.error("No access token found in .env file or environment. Please run 'uv run -m ticktick_mcp.cli auth' to authenticate.")
                    return False
        
        # Initialize the client
        ticktick = TickTickClient(in_memory_only=in_memory_mode)
        
        # Test API connectivity
        projects = ticktick.get_projects()
        if 'error' in projects:
            logger.error(f"Failed to access TickTick API: {projects['error']}")
            logger.error("Your access token may have expired. Please run 'uv run -m ticktick_mcp.cli auth' to refresh it or update your environment variables.")
            return False
            
        return True
    except Exception as e:
        logger.error(f"Failed to initialize TickTick client: {e}")
        return False

# Format a task object from TickTick for better display
def format_task(task: Dict) -> str:
    """Format a task into a human-readable string."""
    formatted = f"Title: {task.get('title', 'No title')}\n"
    
    # Add project ID
    formatted += f"Project ID: {task.get('projectId', 'None')}\n"
    
    # Add dates if available
    if task.get('startDate'):
        formatted += f"Start Date: {task.get('startDate')}\n"
    if task.get('dueDate'):
        formatted += f"Due Date: {task.get('dueDate')}\n"
    
    # Add priority if available
    priority_map = {0: "None", 1: "Low", 3: "Medium", 5: "High"}
    priority = task.get('priority', 0)
    formatted += f"Priority: {priority_map.get(priority, str(priority))}\n"
    
    # Add status if available
    status = "Completed" if task.get('status') == 2 else "Active"
    formatted += f"Status: {status}\n"
    
    # Add content if available
    if task.get('content'):
        formatted += f"\nContent:\n{task.get('content')}\n"
    
    # Add subtasks if available
    items = task.get('items', [])
    if items:
        formatted += f"\nSubtasks ({len(items)}):\n"
        for i, item in enumerate(items, 1):
            status = "✓" if item.get('status') == 1 else "□"
            formatted += f"{i}. [{status}] {item.get('title', 'No title')}\n"
    
    return formatted

# Format a project object from TickTick for better display
def format_project(project: Dict) -> str:
    """Format a project into a human-readable string."""
    formatted = f"Name: {project.get('name', 'No name')}\n"
    formatted += f"ID: {project.get('id', 'No ID')}\n"
    
    # Add color if available
    if project.get('color'):
        formatted += f"Color: {project.get('color')}\n"
    
    # Add view mode if available
    if project.get('viewMode'):
        formatted += f"View Mode: {project.get('viewMode')}\n"
    
    # Add closed status if available
    if 'closed' in project:
        formatted += f"Closed: {'Yes' if project.get('closed') else 'No'}\n"
    
    # Add kind if available
    if project.get('kind'):
        formatted += f"Kind: {project.get('kind')}\n"
    
    return formatted

# MCP Tools

@mcp.call_tool()
async def get_projects(request) -> str:
    """Get all projects from TickTick."""
    if not ticktick:
        if not initialize_client():
            return "Failed to initialize TickTick client. Please check your API credentials."
    
    try:
        projects = ticktick.get_projects()
        if 'error' in projects:
            return f"Error fetching projects: {projects['error']}"
        
        if not projects:
            return "No projects found."
        
        result = f"Found {len(projects)} projects:\n\n"
        for i, project in enumerate(projects, 1):
            result += f"Project {i}:\n" + format_project(project) + "\n"
        
        return result
    except Exception as e:
        return f"Error retrieving projects: {str(e)}"

@mcp.call_tool()
async def get_project(request) -> str:
    project_id = request.get("project_id")
    """
    Get details about a specific project.
    
    Args:
        project_id: ID of the project
    """
    if not ticktick:
        if not initialize_client():
            return "Failed to initialize TickTick client. Please check your API credentials."
    
    try:
        project = ticktick.get_project(project_id)
        if 'error' in project:
            return f"Error fetching project: {project['error']}"
        
        return format_project(project)
    except Exception as e:
        return f"Error retrieving project: {str(e)}"

@mcp.call_tool()
async def get_project_tasks(request) -> str:
    project_id = request.get("project_id")
    """
    Get all tasks in a specific project.
    
    Args:
        project_id: ID of the project
    """
    if not ticktick:
        if not initialize_client():
            return "Failed to initialize TickTick client. Please check your API credentials."
    
    try:
        project_data = ticktick.get_project_with_data(project_id)
        if 'error' in project_data:
            return f"Error fetching project data: {project_data['error']}"
        
        tasks = project_data.get('tasks', [])
        if not tasks:
            return f"No tasks found in project '{project_data.get('project', {}).get('name', project_id)}'."
        
        result = f"Found {len(tasks)} tasks in project '{project_data.get('project', {}).get('name', project_id)}':\n\n"
        for i, task in enumerate(tasks, 1):
            result += f"Task {i}:\n" + format_task(task) + "\n"
        
        return result
    except Exception as e:
        return f"Error retrieving project tasks: {str(e)}"

@mcp.call_tool()
async def get_task(request) -> str:
    project_id = request.get("project_id")
    task_id = request.get("task_id")
    """
    Get details about a specific task.
    
    Args:
        project_id: ID of the project
        task_id: ID of the task
    """
    if not ticktick:
        if not initialize_client():
            return "Failed to initialize TickTick client. Please check your API credentials."
    
    try:
        task = ticktick.get_task(project_id, task_id)
        if 'error' in task:
            return f"Error fetching task: {task['error']}"
        
        return format_task(task)
    except Exception as e:
        return f"Error retrieving task: {str(e)}"

@mcp.call_tool()
async def create_task(request) -> str:
    title = request.get("title")
    project_id = request.get("project_id")
    content = request.get("content")
    start_date = request.get("start_date")
    due_date = request.get("due_date")
    priority = request.get("priority", 0)
    """
    Create a new task in TickTick.
    
    Args:
        title: Task title
        project_id: ID of the project to add the task to
        content: Task description/content (optional)
        start_date: Start date in ISO format YYYY-MM-DDThh:mm:ss+0000 (optional)
        due_date: Due date in ISO format YYYY-MM-DDThh:mm:ss+0000 (optional)
        priority: Priority level (0: None, 1: Low, 3: Medium, 5: High) (optional)
    """
    if not ticktick:
        if not initialize_client():
            return "Failed to initialize TickTick client. Please check your API credentials."
    
    # Validate priority
    if priority not in [0, 1, 3, 5]:
        return "Invalid priority. Must be 0 (None), 1 (Low), 3 (Medium), or 5 (High)."
    
    try:
        # Validate dates if provided
        for date_str, date_name in [(start_date, "start_date"), (due_date, "due_date")]:
            if date_str:
                try:
                    # Try to parse the date to validate it
                    datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                except ValueError:
                    return f"Invalid {date_name} format. Use ISO format: YYYY-MM-DDThh:mm:ss+0000"
        
        task = ticktick.create_task(
            title=title,
            project_id=project_id,
            content=content,
            start_date=start_date,
            due_date=due_date,
            priority=priority
        )
        
        if 'error' in task:
            return f"Error creating task: {task['error']}"
        
        return f"Task created successfully:\n\n" + format_task(task)
    except Exception as e:
        return f"Error creating task: {str(e)}"

@mcp.call_tool()
async def update_task(request) -> str:
    task_id = request.get("task_id")
    project_id = request.get("project_id")
    title = request.get("title")
    content = request.get("content")
    start_date = request.get("start_date")
    due_date = request.get("due_date")
    priority = request.get("priority")
    """
    Update an existing task in TickTick.
    
    Args:
        task_id: ID of the task to update
        project_id: ID of the project the task belongs to
        title: New task title (optional)
        content: New task description/content (optional)
        start_date: New start date in ISO format YYYY-MM-DDThh:mm:ss+0000 (optional)
        due_date: New due date in ISO format YYYY-MM-DDThh:mm:ss+0000 (optional)
        priority: New priority level (0: None, 1: Low, 3: Medium, 5: High) (optional)
    """
    if not ticktick:
        if not initialize_client():
            return "Failed to initialize TickTick client. Please check your API credentials."
    
    # Validate priority if provided
    if priority is not None and priority not in [0, 1, 3, 5]:
        return "Invalid priority. Must be 0 (None), 1 (Low), 3 (Medium), or 5 (High)."
    
    try:
        # Validate dates if provided
        for date_str, date_name in [(start_date, "start_date"), (due_date, "due_date")]:
            if date_str:
                try:
                    # Try to parse the date to validate it
                    datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                except ValueError:
                    return f"Invalid {date_name} format. Use ISO format: YYYY-MM-DDThh:mm:ss+0000"
        
        task = ticktick.update_task(
            task_id=task_id,
            project_id=project_id,
            title=title,
            content=content,
            start_date=start_date,
            due_date=due_date,
            priority=priority
        )
        
        if 'error' in task:
            return f"Error updating task: {task['error']}"
        
        return f"Task updated successfully:\n\n" + format_task(task)
    except Exception as e:
        return f"Error updating task: {str(e)}"

@mcp.call_tool()
async def complete_task(request) -> str:
    project_id = request.get("project_id")
    task_id = request.get("task_id")
    """
    Mark a task as complete.
    
    Args:
        project_id: ID of the project
        task_id: ID of the task
    """
    if not ticktick:
        if not initialize_client():
            return "Failed to initialize TickTick client. Please check your API credentials."
    
    try:
        result = ticktick.complete_task(project_id, task_id)
        if 'error' in result:
            return f"Error completing task: {result['error']}"
        
        return f"Task {task_id} marked as complete."
    except Exception as e:
        return f"Error completing task: {str(e)}"

@mcp.call_tool()
async def delete_task(request) -> str:
    project_id = request.get("project_id")
    task_id = request.get("task_id")
    """
    Delete a task.
    
    Args:
        project_id: ID of the project
        task_id: ID of the task
    """
    if not ticktick:
        if not initialize_client():
            return "Failed to initialize TickTick client. Please check your API credentials."
    
    try:
        result = ticktick.delete_task(project_id, task_id)
        if 'error' in result:
            return f"Error deleting task: {result['error']}"
        
        return f"Task {task_id} deleted successfully."
    except Exception as e:
        return f"Error deleting task: {str(e)}"

@mcp.call_tool()
async def create_project(request) -> str:
    name = request.get("name")
    color = request.get("color", "#F18181")
    view_mode = request.get("view_mode", "list")
    """
    Create a new project in TickTick.
    
    Args:
        name: Project name
        color: Color code (hex format) (optional)
        view_mode: View mode - one of list, kanban, or timeline (optional)
    """
    if not ticktick:
        if not initialize_client():
            return "Failed to initialize TickTick client. Please check your API credentials."
    
    # Validate view_mode
    if view_mode not in ["list", "kanban", "timeline"]:
        return "Invalid view_mode. Must be one of: list, kanban, timeline."
    
    try:
        project = ticktick.create_project(
            name=name,
            color=color,
            view_mode=view_mode
        )
        
        if 'error' in project:
            return f"Error creating project: {project['error']}"
        
        return f"Project created successfully:\n\n" + format_project(project)
    except Exception as e:
        return f"Error creating project: {str(e)}"

@mcp.call_tool()
async def delete_project(request) -> str:
    project_id = request.get("project_id")
    """
    Delete a project.
    
    Args:
        project_id: ID of the project
    """
    if not ticktick:
        if not initialize_client():
            return "Failed to initialize TickTick client. Please check your API credentials."
    
    try:
        result = ticktick.delete_project(project_id)
        if 'error' in result:
            return f"Error deleting project: {result['error']}"
        
        return f"Project {project_id} deleted successfully."
    except Exception as e:
        return f"Error deleting project: {str(e)}"

def main(transport='stdio', host='127.0.0.1', port=3434):
    """
    Main entry point for the MCP server.
    
    Args:
        transport: Transport type ('stdio' or 'sse')
        host: Host to bind to when using SSE transport
        port: Port to use when using SSE transport
    """
    # Initialize the TickTick client
    if not initialize_client():
        logger.error("Failed to initialize TickTick client. Please check your API credentials.")
        return
    
    # Run the server with the specified transport
    if transport == 'sse':
        print(f"Starting TickTick MCP server with SSE transport on {host}:{port}")
        
        # Configure the SSE transport endpoint to match what clients expect
        SseServerTransport.ENDPOINT = "/sse"
        
        # Create an SSE transport
        sse = SseServerTransport("/messages/")
        
        # Define SSE handler
        async def handle_sse(request):
            async with sse.connect_sse(
                request.scope, request.receive, request._send
            ) as streams:
                await mcp.run(streams[0], streams[1], mcp.create_initialization_options())
            return Response()
        
        # Create Starlette app with routes
        from starlette.applications import Starlette
        from starlette.responses import Response
        from starlette.routing import Mount, Route
        
        starlette_app = Starlette(
            debug=True,
            routes=[
                Route("/sse", endpoint=handle_sse, methods=["GET"]),
                Mount("/messages/", app=sse.handle_post_message),
            ]
        )
        
        # Print connection info
        print(f"\n========= CONNECTION INFO =========")
        print(f"Connect to this server at:")
        print(f"URL: http://{host}:{port}")
        print(f"SSE endpoint: {SseServerTransport.ENDPOINT}")
        print(f"=======================================\n")
        
        # Run the Starlette app with Uvicorn
        uvicorn.run(
            starlette_app, 
            host=host, 
            port=port, 
            log_level="info"
        )
    else:
        print("Starting TickTick MCP server with stdio transport")
        # For stdio, we need to run in an async context
        import asyncio
        asyncio.run(mcp.run_stdio(mcp.create_initialization_options()))

if __name__ == "__main__":
    main()