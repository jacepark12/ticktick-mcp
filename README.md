# TickTick MCP Server

A [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) server for TickTick that enables interacting with your TickTick task management system directly through Claude and other MCP clients.

## Features

- 📋 View all your TickTick projects and tasks
- ✏️ Create new projects and tasks through natural language
- 🔄 Update existing task details (title, content, dates, priority)
- ✅ Mark tasks as complete
- 🗑️ Delete tasks and projects
- 🔄 Full integration with TickTick's open API
- 🔌 Seamless integration with Claude and other MCP clients

## Prerequisites

- Python 3.10 or higher
- [uv](https://github.com/astral-sh/uv) - Fast Python package installer and resolver
- TickTick account with API access
- TickTick API credentials (Client ID, Client Secret, Access Token)

## Installation

1. **Clone this repository**:
   ```bash
   git clone https://github.com/jacepark12/ticktick-mcp.git
   cd ticktick-mcp
   ```

2. **Install with uv**:
   ```bash
   # Install uv if you don't have it already
   curl -LsSf https://astral.sh/uv/install.sh | sh

   # Create a virtual environment
   uv venv

   # Activate the virtual environment
   # On macOS/Linux:
   source .venv/bin/activate
   # On Windows:
   .venv\Scripts\activate

   # Install the package
   uv pip install -e .
   ```

3. **Authenticate with TickTick**:
   ```bash
   # Run the authentication flow
   uv run -m ticktick_mcp.cli auth
   ```

   This will:
   - Ask for your TickTick Client ID and Client Secret
   - Open a browser window for you to log in to TickTick
   - Automatically save your access tokens to a `.env` file

4. **Test your configuration**:
   ```bash
   uv run test_server.py
   ```
   This will verify that your TickTick credentials are working correctly.

## Authentication with TickTick

This server uses OAuth2 to authenticate with TickTick. The setup process is straightforward:

1. Register your application at the [TickTick Developer Center](https://developer.ticktick.com/manage)
   - Set the redirect URI to `http://localhost:8000/callback`
   - Note your Client ID and Client Secret

2. Run the authentication command:
   ```bash
   uv run -m ticktick_mcp.cli auth
   ```

3. Follow the prompts to enter your Client ID and Client Secret

4. A browser window will open for you to authorize the application with your TickTick account

5. After authorizing, you'll be redirected back to the application, and your access tokens will be automatically saved to the `.env` file

The server handles token refresh automatically, so you won't need to reauthenticate unless you revoke access or delete your `.env` file.

## Authentication with Dida365

[滴答清单 - Dida365](https://dida365.com/home) is China version of TickTick, and the authentication process is similar to TickTick. Follow these steps to set up Dida365 authentication:

1. Register your application at the [Dida365 Developer Center](https://developer.dida365.com/manage)
   - Set the redirect URI to `http://localhost:8000/callback`
   - Note your Client ID and Client Secret

2. Add environment variables to your `.env` file:
   ```env
   TICKTICK_BASE_URL='https://api.dida365.com/open/v1'
   TICKTICK_AUTH_URL='https://dida365.com/oauth/authorize'
   TICKTICK_TOKEN_URL='https://dida365.com/oauth/token'
   ```

3. Follow the same authentication steps as for TickTick

## Usage with Claude for Desktop

1. Install [Claude for Desktop](https://claude.ai/download)
2. Edit your Claude for Desktop configuration file:

   **macOS**:
   ```bash
   nano ~/Library/Application\ Support/Claude/claude_desktop_config.json
   ```

   **Windows**:
   ```bash
   notepad %APPDATA%\Claude\claude_desktop_config.json
   ```

3. Add the TickTick MCP server configuration, using absolute paths:
   ```json
   {
      "mcpServers": {
         "ticktick": {
            "command": "<absolute path to uv>",
            "args": ["run", "--directory", "<absolute path to ticktick-mcp directory>", "-m", "ticktick_mcp.cli", "run"]
         }
      }
   }
   ```

4. Restart Claude for Desktop

Once connected, you'll see the TickTick MCP server tools available in Claude, indicated by the 🔨 (tools) icon.

## Usage with Docker

The TickTick MCP server can be run in a Docker container, providing a clean, isolated environment for deployment. Docker support includes two main modes: 
1. an interactive authentication mode for initial setup and 
2. a production mode for deployments with pre-configured tokens.

### Option 1: Authorize with Docker

For when authenticating with TickTick using Docker.

#### Requirements for Docker Authentication

- **Web browser access**: You'll need to open a browser to complete the OAuth flow
- **Port 8000 available**: The OAuth callback server needs port 8000 to be free on your host

**Note**: This interactive authentication mode is designed for local development. For production deployments, use the pre-configured tokens approach instead.

#### Authentication Steps

1. **Set up your .env file**:
   ```
   TICKTICK_CLIENT_ID=your_client_id_here
   TICKTICK_CLIENT_SECRET=your_client_secret_here
   ```

2. **Build the Docker image:**
   ```bash
   docker build -t ticktick-mcp:latest .
   ```

3. **Run the authentication:**
   ```bash
   docker run -p 8000:8000 -it -v $(pwd)/.env:/app/.env ticktick-mcp:latest run-with-auth
   ```

The container will:
- Start authentication and display a TickTick OAuth URL
- Wait for you to open the URL in your browser and authorize
- Automatically receive the OAuth callback via port mapping
- Save the access token in the persisted .env file
- Start the MCP server on `http://localhost:8000` to validate the connection

4. **Verify .env variables:**
   Once authentication is complete, your `.env` file will contain:
   ```
   TICKTICK_CLIENT_ID=your_client_id
   TICKTICK_CLIENT_SECRET=your_client_secret
   TICKTICK_ACCESS_TOKEN=generated_access_token
   TICKTICK_REFRESH_TOKEN=generated_refresh_token (if applicable)
   ```

### Option 2: Pre-configured Tokens (Production)

For production deployments where you already have access tokens:

1. **Set up your .env file**:
   ```
   TICKTICK_CLIENT_ID=your_client_id_here
   TICKTICK_CLIENT_SECRET=your_client_secret_here
   TICKTICK_CLIENT_ACCESS_TOKEN=your_access_token_here
   ```

2. **Build the Docker image:**
   ```bash
   docker build -t ticktick-mcp:latest .
   ```

2. **Run the server directly:**
   ```bash
   docker run -p 8000:8000 ticktick-mcp:latest
   ```

This mode skips authentication and directly starts the server, suitable for:
- Production deployments
- Remote containers (Azure Container Apps, AWS ECS, etc.)
- CI/CD environments
- Any scenario where you already have valid OAuth tokens

## Deploy Server locally from source

### Option A: Run as stdio server

```bash
uv run -m ticktick_mcp.cli run --transport stdio
```
This will start the server using the stdio transport, which is suitable for local tools and integrations like Claude Desktop.

### Option B: Run as HTTP server

```bash
uv run -m ticktick_mcp.cli run --transport streamable-http
```
This will start the server using the streamable HTTP transport on the default host and port (`http://localhost:8000/`).

## Available MCP Tools

| Tool | Description | Parameters |
|------|-------------|------------|
| `get_projects` | List all your TickTick projects | None |
| `get_project` | Get details about a specific project | `project_id` |
| `get_project_tasks` | List all tasks in a project | `project_id` |
| `get_task` | Get details about a specific task | `project_id`, `task_id` |
| `create_task` | Create a new task | `title`, `project_id`, `content` (optional), `start_date` (optional), `due_date` (optional), `priority` (optional) |
| `update_task` | Update an existing task | `task_id`, `project_id`, `title` (optional), `content` (optional), `start_date` (optional), `due_date` (optional), `priority` (optional) |
| `complete_task` | Mark a task as complete | `project_id`, `task_id` |
| `delete_task` | Delete a task | `project_id`, `task_id` |
| `create_project` | Create a new project | `name`, `color` (optional), `view_mode` (optional) |
| `delete_project` | Delete a project | `project_id` |

## Task-specific MCP Tools

### Task Retrieval & Search
| Tool | Description | Parameters |
|------|-------------|------------|
| `get_all_tasks` | Get all tasks from all projects | None |
| `get_tasks_by_priority` | Get tasks filtered by priority level | `priority_id` (0: None, 1: Low, 3: Medium, 5: High) |
| `search_tasks` | Search tasks by title, content, or subtasks | `search_term` |

### Date-Based Task Retrieval
| Tool | Description | Parameters |
|------|-------------|------------|
| `get_tasks_due_today` | Get all tasks due today | None |
| `get_tasks_due_tomorrow` | Get all tasks due tomorrow | None |
| `get_tasks_due_in_days` | Get tasks due in exactly X days | `days` (0 = today, 1 = tomorrow, etc.) |
| `get_tasks_due_this_week` | Get tasks due within the next 7 days | None |
| `get_overdue_tasks` | Get all overdue tasks | None |

### Getting Things Done (GTD) Framework
| Tool | Description | Parameters |
|------|-------------|------------|
| `get_engaged_tasks` | Get "engaged" tasks (high priority or overdue) | None |
| `get_next_tasks` | Get "next" tasks (medium priority or due tomorrow) | None |
| `batch_create_tasks` | Create multiple tasks at once | `tasks` (list of task dictionaries) |

## Example Prompts for Claude

Here are some example prompts to use with Claude after connecting the TickTick MCP server:

### General

- "Show me all my TickTick projects"
- "Create a new task called 'Finish MCP server documentation' in my work project with high priority"
- "List all tasks in my personal project"
- "Mark the task 'Buy groceries' as complete"
- "Create a new project called 'Vacation Planning' with a blue color"
- "When is my next deadline in TickTick?"

### Task Filtering Queries

- "What tasks do I have due today?"
- "Show me everything that's overdue"
- "Show me all tasks due this week"
- "Search for tasks about 'project alpha'"
- "Show me all tasks with 'client' in the title or description"
- "Show me all my high priority tasks"

### GTD Workflow

Following David Allen's "Getting Things Done" framework, manage an Engaged and Next actions.

- Engaged will retrieve tasks of high priority, due today or overdue.
- Next will retrieve medium priority or due tomorrow.
- Break down complex actions into smaller actions with batch_creation

For example:

- "Time block the rest of my day from 2-8pm with items from my engaged list"
- "Walk me through my next actions and help my identify what I should focus on tomorrow?" 
- "Break down this project into 5 smaller actionable tasks"

## Development

### Project Structure

```
ticktick-mcp/
├── .env.template          # Template for environment variables
├── README.md              # Project documentation
├── requirements.txt       # Project dependencies
├── setup.py               # Package setup file
├── test_server.py         # Test script for server configuration
└── ticktick_mcp/          # Main package
    ├── __init__.py        # Package initialization
    ├── authenticate.py    # OAuth authentication utility
    ├── cli.py             # Command-line interface
    └── src/               # Source code
        ├── __init__.py    # Module initialization
        ├── auth.py        # OAuth authentication implementation
        ├── server.py      # MCP server implementation
        └── ticktick_client.py  # TickTick API client
```

### Authentication Flow

The project implements a complete OAuth 2.0 flow for TickTick:

1. **Initial Setup**: User provides their TickTick API Client ID and Secret
2. **Browser Authorization**: User is redirected to TickTick to grant access
3. **Token Reception**: A local server receives the OAuth callback with the authorization code
4. **Token Exchange**: The code is exchanged for access and refresh tokens
5. **Token Storage**: Tokens are securely stored in the local `.env` file
6. **Token Refresh**: The client automatically refreshes the access token when it expires

This simplifies the user experience by handling the entire OAuth flow programmatically.

### Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.
