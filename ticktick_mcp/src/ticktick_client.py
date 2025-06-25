import os
import json
import base64
import requests
import logging
import sys
from pathlib import Path
from dotenv import load_dotenv
from typing import Dict, List, Any, Optional, Tuple

# Set up detailed logging for the client
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Add a handler that prints to stdout
handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

class TickTickClient:
    """
    Client for the TickTick API using OAuth2 authentication.
    """
    
    def __init__(self, in_memory_only=False):
        """
        Initialize the TickTick client.
        
        Args:
            in_memory_only: If True, don't save tokens to .env file (useful for containers)
        """
        load_dotenv()
        self.client_id = os.getenv("TICKTICK_CLIENT_ID")
        self.client_secret = os.getenv("TICKTICK_CLIENT_SECRET")
        self.access_token = os.getenv("TICKTICK_ACCESS_TOKEN")
        self.refresh_token = os.getenv("TICKTICK_REFRESH_TOKEN")
        self.in_memory_only = in_memory_only
        
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
        Save the tokens to the .env file or keep them in memory only.
        
        Args:
            tokens: A dictionary containing the access_token and optionally refresh_token
        """
        # If in-memory only mode is enabled, don't save to .env file
        if self.in_memory_only:
            logger.debug("In-memory only mode: tokens not saved to .env file")
            return
            
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
        
        # Log the request details
        logger.debug(f"Making {method} request to {url}")
        logger.debug(f"Headers: {self.headers}")
        if data:
            logger.debug(f"Request data: {json.dumps(data, indent=2)}")
        
        try:
            # Make the request
            if method == "GET":
                logger.debug(f"Sending GET request to {url}")
                response = requests.get(url, headers=self.headers)
            elif method == "POST":
                logger.debug(f"Sending POST request to {url} with data: {data}")
                response = requests.post(url, headers=self.headers, json=data)
            elif method == "DELETE":
                logger.debug(f"Sending DELETE request to {url}")
                response = requests.delete(url, headers=self.headers)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            # Log the response
            logger.debug(f"Response status code: {response.status_code}")
            logger.debug(f"Response headers: {response.headers}")
            
            # Try to log response body if it exists
            try:
                if response.text:
                    logger.debug(f"Response body: {response.text[:1000]}")  # Limit to first 1000 chars
            except Exception as e:
                logger.debug(f"Could not log response body: {e}")
            
            # Check if the request was unauthorized (401)
            if response.status_code == 401:
                logger.info("Access token expired. Attempting to refresh...")
                
                # Try to refresh the access token
                if self._refresh_access_token():
                    logger.debug("Token refreshed, retrying request with new token")
                    logger.debug(f"New authorization header: {self.headers['Authorization']}")
                    
                    # Retry the request with the new token
                    if method == "GET":
                        response = requests.get(url, headers=self.headers)
                    elif method == "POST":
                        response = requests.post(url, headers=self.headers, json=data)
                    elif method == "DELETE":
                        response = requests.delete(url, headers=self.headers)
                    
                    logger.debug(f"Retry response status code: {response.status_code}")
                else:
                    logger.error("Failed to refresh token")
            
            # Raise an exception for 4xx/5xx status codes
            response.raise_for_status()
            
            # Return empty dict for 204 No Content
            if response.status_code == 204:
                logger.debug("Received 204 No Content response")
                return {}
            
            # Log success
            logger.debug(f"Request successful with status {response.status_code}")
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response status code: {e.response.status_code}")
                logger.error(f"Response headers: {e.response.headers}")
                logger.error(f"Response body: {e.response.text}")
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
                   priority: int = 0, is_all_day: bool = False) -> Dict:
        """Creates a new task."""
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
        
        # Add timezone if dates are provided (required by TickTick API)
        if start_date or due_date:
            data["timeZone"] = "UTC"
        
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
