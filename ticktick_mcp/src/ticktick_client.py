import os
import json
import base64
import requests
import logging
from pathlib import Path
from dotenv import load_dotenv
from typing import Dict, List, Any, Optional, Tuple

# Set up logging
logger = logging.getLogger(__name__)

class TickTickClient:
    """
    Client for the TickTick API using OAuth2 authentication.
    """
    
    def __init__(self):
        load_dotenv()
        self.client_id = os.getenv("TICKTICK_CLIENT_ID")
        self.client_secret = os.getenv("TICKTICK_CLIENT_SECRET")
        self.access_token = os.getenv("TICKTICK_ACCESS_TOKEN")
        self.refresh_token = os.getenv("TICKTICK_REFRESH_TOKEN")
        
        if not self.access_token:
            raise ValueError("TICKTICK_ACCESS_TOKEN environment variable is not set. "
                            "Please run 'uv run -m ticktick_mcp.authenticate' to set up your credentials.")
            
        self.base_url = os.getenv("TICKTICK_BASE_URL") or "https://api.ticktick.com/open/v1"
        self.token_url = os.getenv("TICKTICK_TOKEN_URL") or "https://ticktick.com/oauth/token"
        self.headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "Accept-Encoding": None,
            "User-Agent": 'curl/8.7.1'
        }
    
    def _refresh_access_token(self) -> bool:
        """
        Refresh the access token using the refresh token.
        
        Returns:
            True if successful, False otherwise
        """
        if not self.refresh_token:
            logger.warning("No refresh token available. Cannot refresh access token.")
            return False
            
        if not self.client_id or not self.client_secret:
            logger.warning("Client ID or Client Secret missing. Cannot refresh access token.")
            return False
            
        # Prepare the token request
        token_data = {
            "grant_type": "refresh_token",
            "refresh_token": self.refresh_token
        }
        
        # Prepare Basic Auth credentials
        auth_str = f"{self.client_id}:{self.client_secret}"
        auth_bytes = auth_str.encode('ascii')
        auth_b64 = base64.b64encode(auth_bytes).decode('ascii')
        
        headers = {
            "Authorization": f"Basic {auth_b64}",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        
        try:
            # Send the token request
            response = requests.post(self.token_url, data=token_data, headers=headers)
            response.raise_for_status()
            
            # Parse the response
            tokens = response.json()
            
            # Update the tokens
            self.access_token = tokens.get('access_token')
            if 'refresh_token' in tokens:
                self.refresh_token = tokens.get('refresh_token')
                
            # Update the headers
            self.headers["Authorization"] = f"Bearer {self.access_token}"
            
            # Save the tokens to the .env file
            self._save_tokens_to_env(tokens)
            
            logger.info("Access token refreshed successfully.")
            return True
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error refreshing access token: {e}")
            return False
    
    def _save_tokens_to_env(self, tokens: Dict[str, str]) -> None:
        """
        Save the tokens to the .env file.
        
        Args:
            tokens: A dictionary containing the access_token and optionally refresh_token
        """
        # Load existing .env file content
        env_path = Path('.env')
        env_content = {}
        
        if env_path.exists():
            with open(env_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        env_content[key] = value
        
        # Update with new tokens
        env_content["TICKTICK_ACCESS_TOKEN"] = tokens.get('access_token', '')
        if 'refresh_token' in tokens:
            env_content["TICKTICK_REFRESH_TOKEN"] = tokens.get('refresh_token', '')
        
        # Make sure client credentials are saved as well
        if self.client_id and "TICKTICK_CLIENT_ID" not in env_content:
            env_content["TICKTICK_CLIENT_ID"] = self.client_id
        if self.client_secret and "TICKTICK_CLIENT_SECRET" not in env_content:
            env_content["TICKTICK_CLIENT_SECRET"] = self.client_secret
        
        # Write back to .env file
        with open(env_path, 'w') as f:
            for key, value in env_content.items():
                f.write(f"{key}={value}\n")
        
        logger.debug("Tokens saved to .env file")
    
    def _make_request(self, method: str, endpoint: str, data=None) -> Dict:
        """
        Makes a request to the TickTick API.
        
        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint (without base URL)
            data: Request data (for POST, PUT)
        
        Returns:
            API response as a dictionary
        """
        url = f"{self.base_url}{endpoint}"
        
        try:
            # Make the request
            if method == "GET":
                response = requests.get(url, headers=self.headers)
            elif method == "POST":
                response = requests.post(url, headers=self.headers, json=data)
            elif method == "DELETE":
                response = requests.delete(url, headers=self.headers)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            # Check if the request was unauthorized (401)
            if response.status_code == 401:
                logger.info("Access token expired. Attempting to refresh...")
                
                # Try to refresh the access token
                if self._refresh_access_token():
                    # Retry the request with the new token
                    if method == "GET":
                        response = requests.get(url, headers=self.headers)
                    elif method == "POST":
                        response = requests.post(url, headers=self.headers, json=data)
                    elif method == "DELETE":
                        response = requests.delete(url, headers=self.headers)
            
            # Raise an exception for 4xx/5xx status codes
            response.raise_for_status()
            
            # Return empty dict for 204 No Content
            if response.status_code == 204 or response.text == "":
                return {}
            
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {e}")
            return {"error": str(e)}
    
    # Project methods
    def get_projects(self) -> List[Dict]:
        """Gets all projects for the user."""
        return self._make_request("GET", "/project")
    
    def get_project(self, project_id: str) -> Dict:
        """Gets a specific project by ID."""
        return self._make_request("GET", f"/project/{project_id}")
    
    def get_project_with_data(self, project_id: str) -> Dict:
        """Gets project with tasks and columns."""
        return self._make_request("GET", f"/project/{project_id}/data")
    
    def get_project_root_tasks_sort_order(self, project_id: str) -> int:
        """Gets the next available sort order for root tasks in a project."""
        project_data = self.get_project_with_data(project_id)
        if 'error' in project_data:
            return 10000  # Default starting sort order - use larger value to avoid conflicts
        
        tasks = project_data.get('tasks', [])
        if not tasks:
            return 10000
        
        # Find maximum sortOrder among root tasks (those without parentId)
        root_tasks = [task for task in tasks if not task.get('parentId')]
        if root_tasks:
            logger.info(f"Found {len(root_tasks)} root tasks in project {project_id}")
            # Get all sort orders and filter out None/invalid values
            valid_sort_orders = []
            for task in root_tasks:
                sort_order = task.get('sortOrder')
                logger.debug(f"Task {task.get('id', 'unknown')} has sortOrder: {sort_order} (type: {type(sort_order)})")
                if sort_order is not None and isinstance(sort_order, (int, float)):
                    # Only accept reasonable sort order values (positive and not too large)
                    if 0 <= sort_order <= 1000000000:  # Reasonable range
                        valid_sort_orders.append(int(sort_order))
                    else:
                        logger.warning(f"Task {task.get('id')} has unreasonable sortOrder: {sort_order}")
            
            if valid_sort_orders:
                max_sort_order = max(valid_sort_orders)
                next_sort_order = max_sort_order + 10000  # Larger increment to avoid conflicts
                logger.info(f"Max existing valid sort order: {max_sort_order}, next will be: {next_sort_order}")
                return next_sort_order
            else:
                # No valid sort orders found, use a safe starting value
                logger.info("No valid sort orders found, starting with 10000")
                return 10000
        else:
            logger.info("No root tasks found, starting with 10000")
            return 10000
    
    def create_project(self, name: str, color: str = "#F18181", view_mode: str = "list", kind: str = "TASK") -> Dict:
        """Creates a new project."""
        data = {
            "name": name,
            "color": color,
            "viewMode": view_mode,
            "kind": kind
        }
        return self._make_request("POST", "/project", data)
    
    def update_project(self, project_id: str, name: str = None, color: str = None, 
                       view_mode: str = None, kind: str = None) -> Dict:
        """Updates an existing project."""
        data = {}
        if name:
            data["name"] = name
        if color:
            data["color"] = color
        if view_mode:
            data["viewMode"] = view_mode
        if kind:
            data["kind"] = kind
            
        return self._make_request("POST", f"/project/{project_id}", data)
    
    def delete_project(self, project_id: str) -> Dict:
        """Deletes a project."""
        return self._make_request("DELETE", f"/project/{project_id}")
    
    # Task methods
    def get_task(self, project_id: str, task_id: str) -> Dict:
        """Gets a specific task by project ID and task ID."""
        return self._make_request("GET", f"/project/{project_id}/task/{task_id}")
    
    def create_task(self, title: str, project_id: str, content: str = None, 
                   start_date: str = None, due_date: str = None, 
                   priority: int = 0, is_all_day: bool = False, sort_order: int = None) -> Dict:
        """Creates a new task with optional sort order for proper positioning."""
        data = {
            "title": title,
            "projectId": project_id
        }
        
        if content:
            data["content"] = content
        if start_date:
            data["startDate"] = start_date
        if due_date:
            data["dueDate"] = due_date
        if priority is not None:
            data["priority"] = priority
        if is_all_day is not None:
            data["isAllDay"] = is_all_day
        if sort_order is not None:
            data["sortOrder"] = sort_order
            
        return self._make_request("POST", "/task", data)
    
    def update_task(self, task_id: str, project_id: str, title: str = None, 
                   content: str = None, priority: int = None, 
                   start_date: str = None, due_date: str = None) -> Dict:
        """Updates an existing task."""
        data = {
            "id": task_id,
            "projectId": project_id
        }
        
        if title:
            data["title"] = title
        if content:
            data["content"] = content
        if priority is not None:
            data["priority"] = priority
        if start_date:
            data["startDate"] = start_date
        if due_date:
            data["dueDate"] = due_date
            
        return self._make_request("POST", f"/task/{task_id}", data)
    
    def complete_task(self, project_id: str, task_id: str) -> Dict:
        """Marks a task as complete."""
        return self._make_request("POST", f"/project/{project_id}/task/{task_id}/complete")
    
    def delete_task(self, project_id: str, task_id: str) -> Dict:
        """Deletes a task."""
        return self._make_request("DELETE", f"/project/{project_id}/task/{task_id}")
    
    def create_subtask(self, subtask_title: str, parent_task_id: str, project_id: str, 
                      content: str = None, priority: int = 0) -> Dict:
        """
        Creates a subtask for a parent task within the same project.
        Uses tail insertion to maintain order of creation.
        
        Args:
            subtask_title: Title of the subtask
            parent_task_id: ID of the parent task
            project_id: ID of the project (must be same for both parent and subtask)
            content: Optional content/description for the subtask
            priority: Priority level (0-3, where 3 is highest)
        
        Returns:
            API response as a dictionary containing the created subtask
        """
        # First, get the parent task to determine the appropriate sortOrder
        parent_task = self.get_task(project_id, parent_task_id)
        if 'error' in parent_task:
            return parent_task
        
        # Calculate sortOrder for tail insertion with validation
        existing_items = parent_task.get('items', [])
        if existing_items:
            # Filter out unreasonable sortOrder values
            valid_sort_orders = [
                item.get('sortOrder', 0) for item in existing_items 
                if isinstance(item.get('sortOrder'), (int, float)) and 0 <= item.get('sortOrder', 0) <= 1000000000
            ]
            
            if valid_sort_orders:
                max_sort_order = max(valid_sort_orders)
                new_sort_order = max_sort_order + 1000  # Safe increment for tail insertion
            else:
                new_sort_order = 1000  # Safe default
        else:
            # First subtask, use safe base value
            new_sort_order = 1000
        
        data = {
            "title": subtask_title,
            "projectId": project_id,
            "parentId": parent_task_id,
            "sortOrder": new_sort_order
        }
        
        if content:
            data["content"] = content
        if priority is not None:
            data["priority"] = priority
            
        return self._make_request("POST", "/task", data)
    
    def create_subtask_with_order(self, subtask_title: str, parent_task_id: str, project_id: str, 
                                 content: str = None, priority: int = 0, sort_order: int = None) -> Dict:
        """
        Creates a subtask with a specific sort order (more efficient when sort order is pre-calculated).
        
        Args:
            subtask_title: Title of the subtask
            parent_task_id: ID of the parent task
            project_id: ID of the project (must be same for both parent and subtask)
            content: Optional content/description for the subtask
            priority: Priority level (0-3, where 3 is highest)
            sort_order: Pre-calculated sort order for this subtask
        
        Returns:
            API response as a dictionary containing the created subtask
        """
        data = {
            "title": subtask_title,
            "projectId": project_id,
            "parentId": parent_task_id
        }
        
        if content:
            data["content"] = content
        if priority is not None:
            data["priority"] = priority
        if sort_order is not None:
            data["sortOrder"] = sort_order
            
        return self._make_request("POST", "/task", data)
    
    def create_subtasks_batch(self, subtasks_data: List[Dict], parent_task_id: str, project_id: str) -> List[Dict]:
        """
        Creates multiple subtasks for a parent task with proper ordering.
        More efficient than individual calls as it only fetches parent task once.
        
        Args:
            subtasks_data: List of subtask dictionaries with 'title', optional 'content', 'priority'
            parent_task_id: ID of the parent task
            project_id: ID of the project
        
        Returns:
            List of API responses for each created subtask
        """
        # Get the parent task once to determine the starting sortOrder
        parent_task = self.get_task(project_id, parent_task_id)
        if 'error' in parent_task:
            return [parent_task] * len(subtasks_data)
        
        # Calculate starting sortOrder for tail insertion with validation
        existing_items = parent_task.get('items', [])
        print(f"Found {len(existing_items)} existing subtasks for parent task")
        
        if existing_items:
            # Filter out unreasonable sortOrder values
            valid_sort_orders = [
                item.get('sortOrder', 0) for item in existing_items 
                if isinstance(item.get('sortOrder'), (int, float)) and 0 <= item.get('sortOrder', 0) <= 1000000000
            ]
            
            if valid_sort_orders:
                max_sort_order = max(valid_sort_orders)
                base_sort_order = max_sort_order + 1000  # Safe increment
                print(f"Max existing valid sort order: {max_sort_order}, starting new batch at: {base_sort_order}")
            else:
                base_sort_order = 1000  # Safe default
                print(f"No valid sort orders found, using default base: {base_sort_order}")
        else:
            base_sort_order = 1000  # Safe default for first subtask
            print(f"No existing subtasks, using default base: {base_sort_order}")
        
        # Create subtasks with incrementing sortOrder
        results = []
        for i, subtask_info in enumerate(subtasks_data):
            data = {
                "title": subtask_info['title'],
                "projectId": project_id,
                "parentId": parent_task_id,
                "sortOrder": base_sort_order + (i * 100)  # Space them out by 100
            }
            
            if subtask_info.get('content'):
                data["content"] = subtask_info['content']
            if subtask_info.get('priority') is not None:
                data["priority"] = subtask_info['priority']
            
            result = self._make_request("POST", "/task", data)
            results.append(result)
        
        return results