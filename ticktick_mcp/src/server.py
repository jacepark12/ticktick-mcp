import asyncio
import json
import os
import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from typing import Dict, List, Any, Optional
import time
import re
import subprocess

from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv

from .ticktick_client import TickTickClient

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastMCP server
mcp = FastMCP("ticktick")

# Create TickTick client
ticktick = None

import os
from zoneinfo import ZoneInfo

# User timezone configuration  
UTC_TIMEZONE = ZoneInfo("UTC")

def get_user_timezone():
    """Get user timezone from env variable, system detection, or fallback to UTC."""
    # 1. Check .env file first (highest priority)
    env_tz = os.getenv("TICKTICK_USER_TIMEZONE")
    if env_tz:
        try:
            return ZoneInfo(env_tz)
        except Exception:
            logger.warning(f"Invalid timezone in .env: {env_tz}, trying system detection")
    
    # 2. Try to detect system timezone (better method)
    try:
        # Try different methods to get system timezone
        
        # Method 1: Use timedatectl on Linux
        try:
            result = subprocess.run(['timedatectl', 'show', '--property=Timezone', '--value'], 
                                  capture_output=True, text=True, timeout=2)
            if result.returncode == 0 and result.stdout.strip():
                tz_name = result.stdout.strip()
                return ZoneInfo(tz_name)
        except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError):
            pass
        
        # Method 2: Read /etc/timezone on Debian/Ubuntu
        try:
            with open('/etc/timezone', 'r') as f:
                tz_name = f.read().strip()
                if tz_name:
                    return ZoneInfo(tz_name)
        except (FileNotFoundError, PermissionError):
            pass
        
        # Method 3: Parse /etc/localtime symlink
        try:
            import pathlib
            localtime_path = pathlib.Path('/etc/localtime').resolve()
            if 'zoneinfo' in str(localtime_path):
                tz_name = str(localtime_path).split('zoneinfo/')[-1]
                return ZoneInfo(tz_name)
        except Exception:
            pass
        
        # Method 4: Use system time.tzname (less reliable)
        try:
            import time
            system_tz = time.tzname[0] if time.daylight == 0 else time.tzname[1]
            # Try to convert common abbreviations to full names
            tz_mapping = {
                'PST': 'America/Los_Angeles', 'PDT': 'America/Los_Angeles',
                'EST': 'America/New_York', 'EDT': 'America/New_York',
                'CST': 'America/Chicago', 'CDT': 'America/Chicago',
                'MST': 'America/Denver', 'MDT': 'America/Denver',
                'UTC': 'UTC', 'GMT': 'UTC'
            }
            if system_tz in tz_mapping:
                return ZoneInfo(tz_mapping[system_tz])
        except Exception:
            pass
            
    except Exception as e:
        logger.warning(f"System timezone detection failed: {e}")
    
    # 3. Fallback to UTC with clear instruction
    logger.warning("Could not detect system timezone. Using UTC as fallback.")
    logger.warning("To set your timezone, add TICKTICK_USER_TIMEZONE=Your/Timezone to your .env file")
    logger.warning("Examples: TICKTICK_USER_TIMEZONE=America/Los_Angeles (San Francisco)")
    logger.warning("          TICKTICK_USER_TIMEZONE=Europe/London (London)")
    logger.warning("          TICKTICK_USER_TIMEZONE=Asia/Bangkok (Bangkok)")
    
    return ZoneInfo("UTC")

# Get user timezone
USER_TIMEZONE = get_user_timezone()

def initialize_client():
    global ticktick
    try:
        # Check if .env file exists with access token
        load_dotenv()
        
        # Check if we have valid credentials
        if os.getenv("TICKTICK_ACCESS_TOKEN") is None:
            logger.error("No access token found in .env file. Please run 'uv run -m ticktick_mcp.cli auth' to authenticate.")
            return False
        
        # Initialize the client
        ticktick = TickTickClient()
        logger.info("TickTick client initialized successfully")
        logger.info(f"Using timezone: {USER_TIMEZONE}")
        
        # Test API connectivity
        projects = ticktick.get_projects()
        if 'error' in projects:
            logger.error(f"Failed to access TickTick API: {projects['error']}")
            logger.error("Your access token may have expired. Please run 'uv run -m ticktick_mcp.cli auth' to refresh it.")
            return False
            
        logger.info(f"Successfully connected to TickTick API with {len(projects)} projects")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize TickTick client: {e}")
        return False

def normalize_datetime_for_user(date_str: str) -> str:
    """
    Convert date string to UTC if no timezone specified, treating input as user timezone.
    """
    print(f"DEBUG normalize_datetime_for_user INPUT: '{date_str}'")
    
    if not date_str:
        print(f"DEBUG normalize_datetime_for_user OUTPUT (empty): '{date_str}'")
        return date_str
    
    # Если уже есть timezone info, возвращаем как есть
    if not re.search(r'([+-]\d{2}:?\d{2}|Z)$', date_str):
        print(f"DEBUG Timezone NOT found in '{date_str}', starting conversion...")
        try:
            # Парсим как naive datetime (без timezone)
            if 'T' in date_str:
                dt_naive = datetime.fromisoformat(date_str)
                print(f"DEBUG Parsed naive datetime: {dt_naive}")
            else:
                # Обрабатываем формат только даты
                dt_naive = datetime.fromisoformat(date_str + 'T00:00:00')
                print(f"DEBUG Added time to date: {dt_naive}")
            
            # Считаем что это время в timezone пользователя
            dt_user_tz = dt_naive.replace(tzinfo=USER_TIMEZONE)
            print(f"DEBUG Added USER_TIMEZONE: {dt_user_tz}")
            
            # Конвертируем в UTC
            dt_utc = dt_user_tz.astimezone(UTC_TIMEZONE)
            print(f"DEBUG Converted to UTC: {dt_utc}")
            
            # Возвращаем в формате для TickTick API
            result = dt_utc.strftime('%Y-%m-%dT%H:%M:%S.000Z')
            print(f"DEBUG normalize_datetime_for_user OUTPUT (UTC): '{result}'")
            return result
            
        except Exception as e:
            print(f"ERROR in normalize_datetime_for_user: {e}")
            # Если ошибка - возвращаем оригинальную строку с offset (как fallback)
            user_offset = datetime.now(USER_TIMEZONE).strftime('%z')
            if 'T' in date_str:
                result = date_str + user_offset
            else:
                result = date_str + f'T00:00:00{user_offset}'
            print(f"DEBUG normalize_datetime_for_user OUTPUT (fallback): '{result}'")
            return result
    else:
        print(f"DEBUG Timezone found in '{date_str}', returning as-is")
        print(f"DEBUG normalize_datetime_for_user OUTPUT (unchanged): '{date_str}'")
        return date_str
        
# Helper functions for datetime validation and normalization
def validate_datetime_string(date_str: str, field_name: str) -> Optional[str]:
    """Validate datetime string format."""
    if not date_str:
        return None
    try:
        # Try to parse the date to validate it
        datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        return None
    except ValueError:
        return f"Invalid {field_name} format. Use ISO format: YYYY-MM-DDTHH:mm:ss with timezone or YYYY-MM-DD"

# Format a task object from TickTick for better display
def format_task(task: Dict) -> str:
    """Format a task into a human-readable string."""
    formatted = f"ID: {task.get('id', 'No ID')}\n"
    formatted += f"Title: {task.get('title', 'No title')}\n"
    
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

@mcp.tool()
async def get_projects() -> str:
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
        logger.error(f"Error in get_projects: {e}")
        return f"Error retrieving projects: {str(e)}"

@mcp.tool()
async def get_project(project_id: str) -> str:
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
        logger.error(f"Error in get_project: {e}")
        return f"Error retrieving project: {str(e)}"

@mcp.tool()
async def get_project_tasks(project_id: str) -> str:
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
        logger.error(f"Error in get_project_tasks: {e}")
        return f"Error retrieving project tasks: {str(e)}"

@mcp.tool()
async def get_task(project_id: str, task_id: str) -> str:
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
        logger.error(f"Error in get_task: {e}")
        return f"Error retrieving task: {str(e)}"

@mcp.tool()
async def create_task(
    title: str, 
    project_id: str, 
    content: str = None, 
    start_date: str = None, 
    due_date: str = None, 
    priority: int = 0
) -> str:
    """
    Create a new task in TickTick with timezone support.
    
    Args:
        title: Task title
        project_id: ID of the project to add the task to
        content: Task description/content (optional)
        start_date: Start date in ISO format or 'YYYY-MM-DD' (user timezone if no timezone specified) (optional)
        due_date: Due date in ISO format or 'YYYY-MM-DD' (user timezone if no timezone specified) (optional)
        priority: Priority level (0: None, 1: Low, 3: Medium, 5: High) (optional)
    """
    if not ticktick:
        if not initialize_client():
            return "Failed to initialize TickTick client. Please check your API credentials."
    
    # Validate priority
    if priority not in [0, 1, 3, 5]:
        return "Invalid priority. Must be 0 (None), 1 (Low), 3 (Medium), or 5 (High)."
    
    try:
        # Convert dates to user timezone if needed
        if start_date:
            start_date = normalize_datetime_for_user(start_date)
        if due_date:
            due_date = normalize_datetime_for_user(due_date)
            
        # Validate dates if provided
        for date_str, date_name in [(start_date, "start_date"), (due_date, "due_date")]:
            if date_str:
                try:
                    # Try to parse the date to validate it
                    datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                except ValueError:
                    return f"Invalid {date_name} format. Use ISO format: YYYY-MM-DDTHH:mm:ss with timezone or YYYY-MM-DD"
        
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
        logger.error(f"Error in create_task: {e}")
        return f"Error creating task: {str(e)}"

# NEW: Batch create multiple tasks
@mcp.tool()
async def create_multiple_tasks(tasks: List[Dict]) -> str:
    """
    Create multiple tasks in TickTick efficiently.
    
    Args:
        tasks: List of task dictionaries. Each task must contain:
            - title (required): Task title
            - project_id (required): ID of the project to add the task to
            - content (optional): Task description/content
            - start_date (optional): Start date in user timezone (YYYY-MM-DDTHH:mm:ss or with timezone)
            - due_date (optional): Due date in user timezone (YYYY-MM-DDTHH:mm:ss or with timezone)  
            - priority (optional): Priority level (0: None, 1: Low, 3: Medium, 5: High)
    
    Example:
        tasks = [
            {"title": "Task 1", "project_id": "123", "priority": 3},
            {"title": "Task 2", "project_id": "123", "content": "Description", "due_date": "2025-06-15T10:00:00"}
        ]
    """
    if not ticktick:
        if not initialize_client():
            return "Failed to initialize TickTick client. Please check your API credentials."
    
    if not tasks:
        return "No tasks provided to create."
    
    if len(tasks) > 50:
        return "Too many tasks. Maximum 50 tasks per batch for performance."
    
    # Track results
    successful_tasks = []
    failed_tasks = []
    
    logger.info(f"Creating batch of {len(tasks)} tasks")
    
    for i, task_data in enumerate(tasks, 1):
        try:
            # Validate required fields
            if not isinstance(task_data, dict):
                failed_tasks.append({
                    'index': i,
                    'error': 'Task must be a dictionary'
                })
                continue
                
            title = task_data.get('title')
            project_id = task_data.get('project_id')
            
            if not title:
                failed_tasks.append({
                    'index': i,
                    'error': 'Missing required field: title'
                })
                continue
                
            if not project_id:
                failed_tasks.append({
                    'index': i,
                    'error': 'Missing required field: project_id'
                })
                continue
            
            # Extract optional fields with defaults
            content = task_data.get('content')
            start_date = task_data.get('start_date')
            due_date = task_data.get('due_date')
            priority = task_data.get('priority', 0)
            
            # Validate priority
            if priority not in [0, 1, 3, 5]:
                failed_tasks.append({
                    'index': i,
                    'title': title,
                    'error': f'Invalid priority {priority}. Must be 0, 1, 3, or 5'
                })
                continue
            
            # Validate and normalize dates if provided
            # Normalize dates if provided (validation происходит внутри normalize_datetime_for_user)
            normalized_start_date = None
            normalized_due_date = None

            if start_date:
                normalized_start_date = normalize_datetime_for_user(start_date)
                
            if due_date:
                normalized_due_date = normalize_datetime_for_user(due_date)
        
            # Create the task
            task = ticktick.create_task(
                title=title,
                project_id=project_id,
                content=content,
                start_date=normalized_start_date,
                due_date=normalized_due_date,
                priority=priority
            )
            
            if 'error' in task:
                failed_tasks.append({
                    'index': i,
                    'title': title,
                    'error': task['error']
                })
            else:
                successful_tasks.append({
                    'index': i,
                    'title': title,
                    'id': task.get('id'),
                    'task': task
                })
                
        except Exception as e:
            failed_tasks.append({
                'index': i,
                'title': task_data.get('title', 'Unknown'),
                'error': str(e)
            })
    
    # Generate summary report
    result = f"Batch task creation completed:\n"
    result += f"✅ Successful: {len(successful_tasks)}/{len(tasks)} tasks\n"
    result += f"❌ Failed: {len(failed_tasks)}/{len(tasks)} tasks\n\n"
    
    if successful_tasks:
        result += "Successfully created tasks:\n"
        for success in successful_tasks[:5]:  # Show first 5
            result += f"  {success['index']}. {success['title']} (ID: {success['id']})\n"
        if len(successful_tasks) > 5:
            result += f"  ... and {len(successful_tasks) - 5} more\n"
        result += "\n"
    
    if failed_tasks:
        result += "Failed tasks:\n"
        for failure in failed_tasks:
            result += f"  {failure['index']}. {failure['title']}: {failure['error']}\n"
        result += "\n"
    
    return result

# NEW: Batch update multiple tasks
@mcp.tool()
async def update_task_batch(updates: List[Dict]) -> str:
    """
    Update multiple tasks in TickTick efficiently.
    
    Args:
        updates: List of task update dictionaries. Each update must contain:
            - task_id (required): ID of the task to update
            - project_id (required): ID of the project the task belongs to
            - title (optional): New task title
            - content (optional): New task description/content
            - start_date (optional): New start date in user timezone (YYYY-MM-DDTHH:mm:ss or with timezone)
            - due_date (optional): New due date in user timezone (YYYY-MM-DDTHH:mm:ss or with timezone)
            - priority (optional): New priority level (0: None, 1: Low, 3: Medium, 5: High)
    
    Example:
        updates = [
            {"task_id": "123", "project_id": "456", "title": "Updated task 1", "priority": 5},
            {"task_id": "124", "project_id": "456", "due_date": "2025-06-15T10:00:00", "priority": 3}
        ]
    """
    if not ticktick:
        if not initialize_client():
            return "Failed to initialize TickTick client. Please check your API credentials."
    
    if not updates:
        return "No updates provided."
    
    if len(updates) > 50:
        return "Too many task updates. Maximum 50 tasks per batch for performance."
    
    # Track results
    successful_updates = []
    failed_updates = []
    
    logger.info(f"Updating batch of {len(updates)} tasks")
    
    for i, update_data in enumerate(updates, 1):
        try:
            # Validate required fields
            if not isinstance(update_data, dict):
                failed_updates.append({
                    'index': i,
                    'error': 'Update must be a dictionary'
                })
                continue
                
            task_id = update_data.get('task_id')
            project_id = update_data.get('project_id')
            
            if not task_id:
                failed_updates.append({
                    'index': i,
                    'error': 'Missing required field: task_id'
                })
                continue
                
            if not project_id:
                failed_updates.append({
                    'index': i,
                    'error': 'Missing required field: project_id'
                })
                continue
            
            # Extract optional fields
            title = update_data.get('title')
            content = update_data.get('content')
            start_date = update_data.get('start_date')
            due_date = update_data.get('due_date')
            priority = update_data.get('priority')
            
            # Validate priority if provided
            if priority is not None and priority not in [0, 1, 3, 5]:
                failed_updates.append({
                    'index': i,
                    'task_id': task_id,
                    'error': f'Invalid priority {priority}. Must be 0, 1, 3, or 5'
                })
                continue
            
            # Validate and normalize dates if provided
            normalized_start_date = None
            normalized_due_date = None
            
            if start_date:
                validation_error = validate_datetime_string(start_date, "start_date")
                if validation_error:
                    failed_updates.append({
                        'index': i,
                        'task_id': task_id,
                        'error': validation_error
                    })
                    continue
                normalized_start_date = normalize_datetime_for_user(start_date)
            
            if due_date:
                validation_error = validate_datetime_string(due_date, "due_date")
                if validation_error:
                    failed_updates.append({
                        'index': i,
                        'task_id': task_id,
                        'error': validation_error
                    })
                    continue
                normalized_due_date = normalize_datetime_for_user(due_date)
            
            # Update the task
            result = ticktick.update_task(
                task_id=task_id,
                project_id=project_id,
                title=title,
                content=content,
                start_date=normalized_start_date,
                due_date=normalized_due_date,
                priority=priority
            )
            
            if 'error' in result:
                failed_updates.append({
                    'index': i,
                    'task_id': task_id,
                    'error': result['error']
                })
            else:
                successful_updates.append({
                    'index': i,
                    'task_id': task_id,
                    'title': title or result.get('title', 'Unknown'),
                    'task': result
                })
                
        except Exception as e:
            failed_updates.append({
                'index': i,
                'task_id': update_data.get('task_id', 'Unknown'),
                'error': str(e)
            })
    
    # Generate summary report
    result = f"Batch task update completed:\n"
    result += f"✅ Successful: {len(successful_updates)}/{len(updates)} tasks\n"
    result += f"❌ Failed: {len(failed_updates)}/{len(updates)} tasks\n\n"
    
    if successful_updates:
        result += "Successfully updated tasks:\n"
        for success in successful_updates[:5]:  # Show first 5
            result += f"  {success['index']}. {success['title']} (ID: {success['task_id']})\n"
        if len(successful_updates) > 5:
            result += f"  ... and {len(successful_updates) - 5} more\n"
        result += "\n"
    
    if failed_updates:
        result += "Failed updates:\n"
        for failure in failed_updates:
            result += f"  {failure['index']}. {failure['task_id']}: {failure['error']}\n"
        result += "\n"
    
    return result

# NEW: Search tasks by text
@mcp.tool()
async def search_tasks(
    query: str, 
    project_id: str = None,
    include_completed: bool = False
) -> str:
    """
    Search for tasks by title or content text.
    
    Args:
        query: Text to search for in task titles and content
        project_id: Optional project ID to limit search scope
        include_completed: Whether to include completed tasks (default: False)
    """
    if not ticktick:
        if not initialize_client():
            return "Failed to initialize TickTick client. Please check your API credentials."
    
    try:
        # Get all projects or specific project
        if project_id:
            project_data = ticktick.get_project_with_data(project_id)
            if 'error' in project_data:
                return f"Error fetching project: {project_data['error']}"
            all_tasks = project_data.get('tasks', [])
            search_scope = f"project '{project_data.get('project', {}).get('name', project_id)}'"
        else:
            # Get tasks from all projects
            projects = ticktick.get_projects()
            if 'error' in projects:
                return f"Error fetching projects: {projects['error']}"
            
            all_tasks = []
            for project in projects:
                project_data = ticktick.get_project_with_data(project['id'])
                if 'error' not in project_data:
                    all_tasks.extend(project_data.get('tasks', []))
            search_scope = "all projects"
        
        # Filter tasks based on search criteria
        matching_tasks = []
        query_lower = query.lower()
        
        for task in all_tasks:
            # Skip completed tasks unless requested
            if not include_completed and task.get('status') == 2:
                continue
                
            # Search in title and content
            title = task.get('title', '').lower()
            content = task.get('content', '').lower()
            
            if query_lower in title or query_lower in content:
                matching_tasks.append(task)
        
        # Format results
        if not matching_tasks:
            return f"No tasks found matching '{query}' in {search_scope}."
        
        result = f"Found {len(matching_tasks)} tasks matching '{query}' in {search_scope}:\n\n"
        
        for i, task in enumerate(matching_tasks[:10], 1):  # Limit to first 10
            result += f"Task {i}:\n" + format_task(task) + "\n"
        
        if len(matching_tasks) > 10:
            result += f"... and {len(matching_tasks) - 10} more matching tasks\n"
        
        return result
        
    except Exception as e:
        logger.error(f"Error in search_tasks: {e}")
        return f"Error searching tasks: {str(e)}"

# NEW: Get overdue tasks
@mcp.tool()
async def get_overdue_tasks(project_id: str = None) -> str:
    """
    Get all overdue tasks (tasks with due dates in the past).
    
    Args:
        project_id: Optional project ID to limit scope (default: all projects)
    """
    if not ticktick:
        if not initialize_client():
            return "Failed to initialize TickTick client. Please check your API credentials."
    
    try:
        # Get current time in user timezone
        now = datetime.now(USER_TIMEZONE)
        
        # Get tasks
        if project_id:
            project_data = ticktick.get_project_with_data(project_id)
            if 'error' in project_data:
                return f"Error fetching project: {project_data['error']}"
            all_tasks = project_data.get('tasks', [])
            scope = f"project '{project_data.get('project', {}).get('name', project_id)}'"
        else:
            # Get from all projects  
            projects = ticktick.get_projects()
            if 'error' in projects:
                return f"Error fetching projects: {projects['error']}"
            
            all_tasks = []
            for project in projects:
                project_data = ticktick.get_project_with_data(project['id'])
                if 'error' not in project_data:
                    all_tasks.extend(project_data.get('tasks', []))
            scope = "all projects"
        
        # Find overdue tasks
        overdue_tasks = []
        for task in all_tasks:
            # Skip completed tasks
            if task.get('status') == 2:
                continue
                
            due_date_str = task.get('dueDate')
            if due_date_str:
                try:
                    # Parse due date
                    due_date = datetime.fromisoformat(due_date_str.replace('Z', '+00:00'))
                    
                    # Convert to user timezone for comparison
                    if due_date.tzinfo is None:
                        due_date = due_date.replace(tzinfo=USER_TIMEZONE)
                    else:
                        due_date = due_date.astimezone(USER_TIMEZONE)
                    
                    # Check if overdue
                    if due_date < now:
                        overdue_tasks.append((task, due_date))
                        
                except (ValueError, TypeError):
                    continue  # Skip invalid dates
        
        # Sort by due date (most overdue first)
        overdue_tasks.sort(key=lambda x: x[1])
        
        if not overdue_tasks:
            return f"🎉 No overdue tasks found in {scope}!"
        
        result = f"⚠️ Found {len(overdue_tasks)} overdue tasks in {scope}:\n\n"
        
        for i, (task, due_date) in enumerate(overdue_tasks, 1):
            days_overdue = (now - due_date).days
            result += f"Task {i} (⏰ {days_overdue} days overdue):\n" + format_task(task) + "\n"
        
        return result
        
    except Exception as e:
        logger.error(f"Error in get_overdue_tasks: {e}")
        return f"Error getting overdue tasks: {str(e)}"

# NEW: Get today's tasks
@mcp.tool()
async def get_today_tasks(project_id: str = None) -> str:
    """
    Get all tasks due today (user timezone).
    
    Args:
        project_id: Optional project ID to limit scope (default: all projects)
    """
    if not ticktick:
        if not initialize_client():
            return "Failed to initialize TickTick client. Please check your API credentials."
    
    try:
        # Get current date in user timezone
        today = datetime.now(USER_TIMEZONE).date()
        
        # Get tasks
        if project_id:
            project_data = ticktick.get_project_with_data(project_id)
            if 'error' in project_data:
                return f"Error fetching project: {project_data['error']}"
            all_tasks = project_data.get('tasks', [])
            scope = f"project '{project_data.get('project', {}).get('name', project_id)}'"
        else:
            # Get from all projects
            projects = ticktick.get_projects()
            if 'error' in projects:
                return f"Error fetching projects: {projects['error']}"
            
            all_tasks = []
            for project in projects:
                project_data = ticktick.get_project_with_data(project['id'])
                if 'error' not in project_data:
                    all_tasks.extend(project_data.get('tasks', []))
            scope = "all projects"
        
        # Find today's tasks
        today_tasks = []
        for task in all_tasks:
            # Skip completed tasks
            if task.get('status') == 2:
                continue
                
            due_date_str = task.get('dueDate')
            if due_date_str:
                try:
                    # Parse due date
                    due_date = datetime.fromisoformat(due_date_str.replace('Z', '+00:00'))
                    
                    # Convert to user timezone
                    if due_date.tzinfo is None:
                        due_date = due_date.replace(tzinfo=USER_TIMEZONE)
                    else:
                        due_date = due_date.astimezone(USER_TIMEZONE)
                    
                    # Check if due today
                    if due_date.date() == today:
                        today_tasks.append(task)
                        
                except (ValueError, TypeError):
                    continue  # Skip invalid dates
        
        if not today_tasks:
            return f"📅 No tasks due today in {scope}."
        
        result = f"📅 Found {len(today_tasks)} tasks due today in {scope}:\n\n"
        
        for i, task in enumerate(today_tasks, 1):
            result += f"Task {i}:\n" + format_task(task) + "\n"
        
        return result
        
    except Exception as e:
        logger.error(f"Error in get_today_tasks: {e}")
        return f"Error getting today's tasks: {str(e)}"

# NEW: Оптимизированная функция get_upcoming_tasks
@mcp.tool()
async def get_upcoming_tasks(days: int = 7, project_id: str = None) -> str:
    """
    Get all tasks due in the next N days (user timezone).
    
    Args:
        days: Number of days to look ahead (default: 7)
        project_id: Optional project ID to limit scope (default: all projects)
    """
    if not ticktick:
        if not initialize_client():
            return "Failed to initialize TickTick client. Please check your API credentials."
    
    if days <= 0:
        return "Days must be a positive number."
    
    if days > 365:
        return "Days cannot exceed 365 for performance reasons."
    
    try:
        # Get current time and future cutoff in user timezone
        now = datetime.now(USER_TIMEZONE)
        future_cutoff = now + timedelta(days=days)
        
        # Get tasks
        if project_id:
            project_data = ticktick.get_project_with_data(project_id)
            if 'error' in project_data:
                return f"Error fetching project: {project_data['error']}"
            all_tasks = project_data.get('tasks', [])
            scope = f"project '{project_data.get('project', {}).get('name', project_id)}'"
        else:
            # Get from all projects - OPTIMIZED VERSION
            projects = ticktick.get_projects()
            if 'error' in projects:
                return f"Error fetching projects: {projects['error']}"
            
            # 🚀 OPTIMIZATION 1: Filter only active (non-closed) projects
            active_projects = [p for p in projects if not p.get('closed', False)]
            original_count = len(projects)
            active_count = len(active_projects)
            
            logger.info(f"Found {original_count} total projects, {active_count} active projects")
            
            # 🚀 OPTIMIZATION 2: Limit quantity for performance (configurable)
            PROJECT_LIMIT = int(os.getenv('TICKTICK_PROJECT_LIMIT', '20'))
            
            if len(active_projects) > PROJECT_LIMIT:
                logger.info(f"Limiting search to first {PROJECT_LIMIT} active projects out of {active_count} total active projects")
                limited_projects = active_projects[:PROJECT_LIMIT]
                scope = f"{PROJECT_LIMIT} active projects (limited for performance, {active_count - PROJECT_LIMIT} projects skipped)"
            else:
                limited_projects = active_projects
                scope = f"{len(limited_projects)} active projects"
            
            # 🚀 OPTIMIZATION 3: Improved error handling with partial results
            all_tasks = []
            failed_projects = 0
            successful_projects = 0
            
            logger.info(f"Processing {len(limited_projects)} projects...")
            
            for i, project in enumerate(limited_projects, 1):
                try:
                    logger.debug(f"Processing project {i}/{len(limited_projects)}: {project.get('name', 'Unknown')}")
                    project_data = ticktick.get_project_with_data(project['id'])
                    
                    if 'error' not in project_data:
                        project_tasks = project_data.get('tasks', [])
                        all_tasks.extend(project_tasks)
                        successful_projects += 1
                        logger.debug(f"✅ Project '{project.get('name')}': {len(project_tasks)} tasks")
                    else:
                        failed_projects += 1
                        logger.warning(f"❌ Project '{project.get('name')}' returned error: {project_data['error']}")
                        
                except Exception as e:
                    failed_projects += 1
                    logger.warning(f"❌ Failed to fetch project '{project.get('name', project['id'])}': {str(e)}")
                    continue
            
            logger.info(f"Completed processing: {successful_projects} successful, {failed_projects} failed")
        
        # Find upcoming tasks
        upcoming_tasks = []
        for task in all_tasks:
            # Skip completed tasks
            if task.get('status') == 2:
                continue
                
            due_date_str = task.get('dueDate')
            if due_date_str:
                try:
                    # Parse due date
                    due_date = datetime.fromisoformat(due_date_str.replace('Z', '+00:00'))
                    
                    # Convert to user timezone
                    if due_date.tzinfo is None:
                        due_date = due_date.replace(tzinfo=USER_TIMEZONE)
                    else:
                        due_date = due_date.astimezone(USER_TIMEZONE)
                    
                    # Check if due within the specified days
                    if now <= due_date <= future_cutoff:
                        upcoming_tasks.append((task, due_date))
                        
                except (ValueError, TypeError):
                    continue  # Skip invalid dates
        
        # Sort by due date (earliest first)
        upcoming_tasks.sort(key=lambda x: x[1])
        
        # 🚀 OPTIMIZATION 4: Enhanced result reporting
        result = f"📅 Found {len(upcoming_tasks)} tasks due in the next {days} day{'s' if days != 1 else ''} in {scope}"
        
        # Add performance statistics
        if not project_id:
            result += f"\n📊 Performance stats: {successful_projects} projects processed"
            if failed_projects > 0:
                result += f", {failed_projects} projects skipped due to errors"
            if len(active_projects) > PROJECT_LIMIT:
                result += f"\n⚠️ Note: Limited to {PROJECT_LIMIT} projects for performance. Set TICKTICK_PROJECT_LIMIT in .env to change this limit."
        
        if not upcoming_tasks:
            result += "."
            return result
        
        result += ":\n\n"
        
        # Group by date for better readability
        current_date = None
        for i, (task, due_date) in enumerate(upcoming_tasks, 1):
            task_date = due_date.date()
            
            # Add date header if this is a new date
            if current_date != task_date:
                current_date = task_date
                days_from_now = (task_date - now.date()).days
                
                if days_from_now == 0:
                    date_label = "📍 Today"
                elif days_from_now == 1:
                    date_label = "📍 Tomorrow"
                else:
                    date_label = f"📍 {task_date.strftime('%A, %B %d')} ({days_from_now} days)"
                
                result += f"\n{date_label}:\n"
            
            # Format task info
            time_str = due_date.strftime('%H:%M') if due_date.hour != 0 or due_date.minute != 0 else "All day"
            priority_emoji = {0: "⚪", 1: "🔵", 3: "🟡", 5: "🔴"}.get(task.get('priority', 0), "⚪")
            
            result += f"  {priority_emoji} {task.get('title', 'No title')} ({time_str})\n"
            
            # Add project info if showing all projects
            if not project_id:
                result += f"    📁 Project ID: {task.get('projectId', 'Unknown')}\n"
            
            # Add content if available (truncated)
            content = task.get('content', '')
            if content:
                content_preview = content[:50] + "..." if len(content) > 50 else content
                result += f"    📝 {content_preview}\n"
        
        return result
        
    except Exception as e:
        logger.error(f"Error in get_upcoming_tasks: {e}")
        return f"Error getting upcoming tasks: {str(e)}"

@mcp.tool()
async def update_task(
    task_id: str,
    project_id: str,
    title: str = None,
    content: str = None,
    start_date: str = None,
    due_date: str = None,
    priority: int = None
) -> str:
    """
    Update an existing task in TickTick with timezone support.
    
    Args:
        task_id: ID of the task to update
        project_id: ID of the project the task belongs to
        title: New task title (optional)
        content: New task description/content (optional)
        start_date: New start date in ISO format or 'YYYY-MM-DD' (user timezone if no timezone specified) (optional)
        due_date: New due date in ISO format or 'YYYY-MM-DD' (user timezone if no timezone specified) (optional)
        priority: New priority level (0: None, 1: Low, 3: Medium, 5: High) (optional)
    """
    if not ticktick:
        if not initialize_client():
            return "Failed to initialize TickTick client. Please check your API credentials."
    
    # Validate priority if provided
    if priority is not None and priority not in [0, 1, 3, 5]:
        return "Invalid priority. Must be 0 (None), 1 (Low), 3 (Medium), or 5 (High)."
    
    try:
        # Convert dates to user timezone if needed
        if start_date:
            start_date = normalize_datetime_for_user(start_date)
        if due_date:
            due_date = normalize_datetime_for_user(due_date)
            
        # Validate dates if provided
        for date_str, date_name in [(start_date, "start_date"), (due_date, "due_date")]:
            if date_str:
                try:
                    # Try to parse the date to validate it
                    datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                except ValueError:
                    return f"Invalid {date_name} format. Use ISO format: YYYY-MM-DDTHH:mm:ss with timezone or YYYY-MM-DD"
        
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
        logger.error(f"Error in update_task: {e}")
        return f"Error updating task: {str(e)}"

@mcp.tool()
async def complete_task(project_id: str, task_id: str) -> str:
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
        logger.error(f"Error in complete_task: {e}")
        return f"Error completing task: {str(e)}"

@mcp.tool()
async def delete_task(project_id: str, task_id: str) -> str:
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
        logger.error(f"Error in delete_task: {e}")
        return f"Error deleting task: {str(e)}"

@mcp.tool()
async def create_project(
    name: str,
    color: str = "#F18181",
    view_mode: str = "list"
) -> str:
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
        logger.error(f"Error in create_project: {e}")
        return f"Error creating project: {str(e)}"

@mcp.tool()
async def delete_project(project_id: str) -> str:
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
        logger.error(f"Error in delete_project: {e}")
        return f"Error deleting project: {str(e)}"

def main():
    """Main entry point for the MCP server."""
    # Initialize the TickTick client
    if not initialize_client():
        logger.error("Failed to initialize TickTick client. Please check your API credentials.")
        return
    
    # Run the server
    mcp.run(transport='stdio')

if __name__ == "__main__":
    main()
