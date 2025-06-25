# TickTick MCP Server

A powerful [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) server that enables seamless integration between Claude Desktop and TickTick task management system.

<div align="center">

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.10+-blue.svg)
![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey.svg)

</div>

## ✨ Features

### 🔥 **New Enhanced Features**
- **🌍 Smart Timezone Support** - Automatic timezone detection with manual override options
- **⚡ Batch Operations** - Create/update multiple tasks simultaneously 
- **🔍 Advanced Search** - Find tasks by title, content, or project with filters
- **📊 Analytics & Insights** - Project statistics, overdue tracking, productivity metrics
- **📅 Smart Scheduling** - Get today's tasks, upcoming deadlines, overdue items

### 📋 **Core Task Management**
- **Full CRUD Operations** - Create, read, update, delete tasks and projects
- **Priority Management** - Set and modify task priorities (None, Low, Medium, High)
- **Date & Time Handling** - Start dates, due dates with timezone awareness
- **Project Organization** - Manage multiple projects with different view modes
- **Task Completion** - Mark tasks as complete with automatic timestamps

### 🔄 **Seamless Integration**
- **Natural Language Commands** - Control TickTick through conversational Claude interface
- **Real-time Synchronization** - Changes reflect immediately in TickTick apps
- **OAuth2 Authentication** - Secure, token-based authentication with auto-refresh
- **Error Handling** - Robust error recovery and user-friendly messages

## 🚀 Quick Start

### Prerequisites

- **Python 3.10+**
- **[uv](https://github.com/astral-sh/uv)** - Fast Python package manager
- **[Claude Desktop](https://claude.ai/download)** 
- **TickTick Account** with API access

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/jacepark12/ticktick-mcp.git
   cd ticktick-mcp
   ```

2. **Create and activate virtual environment**
   ```bash
   uv venv
   # On Windows:
   .venv\Scripts\activate
   # On macOS/Linux:
   source .venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   uv pip install -e .
   uv pip install tzdata  # For timezone support
   ```

4. **Set up TickTick API credentials**

   Register your application at [TickTick Developer Center](https://developer.ticktick.com/manage):
   - Set redirect URI to: `http://localhost:8000/callback`
   - Note your Client ID and Client Secret

5. **Authenticate with TickTick**
   ```bash
   uv run -m ticktick_mcp.cli auth
   ```
   
   This will:
   - Prompt for your Client ID and Client Secret
   - Open browser for TickTick authorization
   - Automatically save tokens to `.env` file

6. **Test the setup**
   ```bash
   uv run test_server.py
   ```

### Claude Desktop Configuration

1. **Find uv path**
   ```bash
   # Windows
   where uv
   # macOS/Linux  
   which uv
   ```

2. **Edit Claude Desktop config**

   **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
   
   **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

   ```json
   {
     "mcpServers": {
       "ticktick": {
         "command": "/path/to/uv",
         "args": ["run", "--directory", "/path/to/ticktick-mcp", "-m", "ticktick_mcp.cli", "run"]
       }
     }
   }
   ```

3. **Restart Claude Desktop**

## 🎯 Usage Examples

### Basic Operations
```
"Show me all my TickTick projects"
"Create a task 'Buy groceries' in my Personal project"
"List all tasks in my Work project"
"Mark task 'Complete report' as done"
```

### Advanced Features
```
"Create 5 tasks for my morning routine in Personal project"
"Show me all overdue tasks"
"Find all tasks containing 'meeting'"
"What tasks do I have due today?"
"Show statistics for my Work project"
"Get upcoming tasks for next 7 days"
```

### Batch Operations
```
"Create multiple tasks: 'Review code', 'Write tests', 'Deploy to staging' all in Development project"
"Update all overdue tasks to be due tomorrow with high priority"
```

### Analytics & Insights
```
"Show project statistics for Work"
"Which tasks are overdue across all projects?"
"What's my completion rate this month?"
"Show me upcoming deadlines for next week"
```

## 🛠 Available Tools

<details>
<summary><strong>📝 Task Management</strong></summary>

| Tool | Description | Parameters |
|------|-------------|-------------|
| `get_task` | Get specific task details | `project_id`, `task_id` |
| `create_task` | Create new task | `title`, `project_id`, `content?`, `start_date?`, `due_date?`, `priority?` |
| `update_task` | Update existing task | `task_id`, `project_id`, `title?`, `content?`, `start_date?`, `due_date?`, `priority?` |
| `complete_task` | Mark task as complete | `project_id`, `task_id` |
| `delete_task` | Delete task | `project_id`, `task_id` |

</details>

<details>
<summary><strong>📁 Project Management</strong></summary>

## Docker Usage

You can run the TickTick MCP server inside a Docker container using the SSE transport option:

1. **Build the Docker image**:
   ```bash
   docker build -t ticktick-mcp .
   ```

2. **Run the container with SSE transport**:
   ```bash
   docker run -p 3434:3434 -v $(pwd)/.env:/app/.env ticktick-mcp uv run -m ticktick_mcp.cli run --transport sse --host 0.0.0.0 --port 3434
   ```

3. **Configure Claude to connect to the containerized server**:
   Edit your Claude configuration file and add the following:
   ```json
   {
      "mcpServers": {
         "ticktick": {
            "url": "http://localhost:3434"
         }
      }
   }
   ```

4. **Authentication in Docker**:
   You have two options for authentication in Docker:
   
   **Option 1: Mount .env file from host**
   Run the authentication process outside of Docker to create the `.env` file, then mount it:
   ```bash
   # On your host machine
   uv run -m ticktick_mcp.cli auth
   
   # Then run Docker with the .env file mounted
   docker run -p 3434:3434 -v $(pwd)/.env:/app/.env ticktick-mcp
   ```
   
   **Option 2: Pass environment variables directly**
   Pass the TickTick authentication tokens as environment variables:
   ```bash
   docker run -p 3434:3434 \
     -e TICKTICK_CLIENT_ID=your_client_id \
     -e TICKTICK_CLIENT_SECRET=your_client_secret \
     -e TICKTICK_ACCESS_TOKEN=your_access_token \
     -e TICKTICK_REFRESH_TOKEN=your_refresh_token \
     ghcr.io/egv/ticktick-mcp:latest
   ```

### Docker Compose Example

**Option 1: With mounted .env file**
```yaml
services:
  ticktick-mcp:
    build: .
    ports:
      - "3434:3434"
    volumes:
      - ./.env:/app/.env
    command: uv run -m ticktick_mcp.cli run --transport sse --host 0.0.0.0 --port 3434
```

**Option 2: With environment variables**
```yaml
services:
  ticktick-mcp:
    image: ghcr.io/egv/ticktick-mcp:latest
    ports:
      - "3434:3434"
    environment:
      - TICKTICK_CLIENT_ID=your_client_id
      - TICKTICK_CLIENT_SECRET=your_client_secret
      - TICKTICK_ACCESS_TOKEN=your_access_token
      - TICKTICK_REFRESH_TOKEN=your_refresh_token
    restart: unless-stopped
```

### Using the GitHub Container Registry Image

The Docker image is automatically built and published to GitHub Container Registry. You can use the pre-built image instead of building it yourself:

```bash
# Pull the latest image
docker pull ghcr.io/egv/ticktick-mcp:latest

# Run with SSE transport
docker run -p 3434:3434 -v $(pwd)/.env:/app/.env ghcr.io/egv/ticktick-mcp:latest
```

Or in your docker-compose.yml:

```yaml
services:
  ticktick-mcp:
    image: ghcr.io/egv/ticktick-mcp:latest
    ports:
      - "3434:3434"
    volumes:
      - ./.env:/app/.env
    restart: unless-stopped
```

## Available MCP Tools
| Tool | Description | Parameters |
|------|-------------|-------------|
| `get_projects` | List all projects | None |
| `get_project` | Get specific project | `project_id` |
| `get_project_tasks` | Get all tasks in project | `project_id` |
| `create_project` | Create new project | `name`, `color?`, `view_mode?` |
| `delete_project` | Delete project | `project_id` |

</details>

<details>
<summary><strong>⚡ Batch Operations</strong></summary>

| Tool | Description | Parameters |
|------|-------------|-------------|
| `create_multiple_tasks` | Create multiple tasks efficiently | `tasks` (array of task objects) |
| `update_task_batch` | Update multiple tasks at once | `updates` (array of update objects) |

</details>

<details>
<summary><strong>🔍 Search & Analytics</strong></summary>

| Tool | Description | Parameters |
|------|-------------|-------------|
| `search_tasks` | Search tasks by content/title | `query`, `project_id?`, `include_completed?` |
| `get_overdue_tasks` | Get all overdue tasks | `project_id?` |
| `get_today_tasks` | Get tasks due today | `project_id?` |
| `get_upcoming_tasks` | Get tasks due in next N days | `days?`, `project_id?` |
| `get_project_stats` | Get detailed project statistics | `project_id` |

</details>

## ⚙️ Configuration

### Timezone Settings

Set your timezone in `.env` file:
```env
TICKTICK_USER_TIMEZONE=America/New_York  # Eastern Time
TICKTICK_USER_TIMEZONE=Europe/London     # GMT
TICKTICK_USER_TIMEZONE=Asia/Tokyo        # JST
```

**Auto-detection**: If not set, the system will attempt to detect your timezone automatically.

### Dida365 Support

For users of [Dida365](https://dida365.com/) (Chinese version of TickTick):

1. Register at [Dida365 Developer Center](https://developer.dida365.com/manage)
2. Add to your `.env` file:
   ```env
   TICKTICK_BASE_URL=https://api.dida365.com/open/v1
   TICKTICK_AUTH_URL=https://dida365.com/oauth/authorize
   TICKTICK_TOKEN_URL=https://dida365.com/oauth/token
   ```

## 🔧 Troubleshooting

### Common Issues

<details>
<summary><strong>"Server disconnected" in Claude Desktop</strong></summary>

**Solutions:**
1. Check uv path: `where uv` (Windows) or `which uv` (macOS/Linux)
2. Verify config file uses correct absolute paths
3. Use forward slashes `/` in JSON paths
4. Completely restart Claude Desktop
5. Check logs: Click "Open Logs Folder" in Claude Desktop

</details>

<details>
<summary><strong>"Access token expired"</strong></summary>

**Solution:**
```bash
cd ticktick-mcp
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
uv run -m ticktick_mcp.cli auth
```

</details>

<details>
<summary><strong>"ZoneInfoNotFoundError"</strong></summary>

**Solution:**
```bash
uv pip install tzdata
```

</details>

<details>
<summary><strong>"No virtual environment found"</strong></summary>

**Solution:**
```bash
cd ticktick-mcp
uv venv
.venv\Scripts\activate  # Windows
# or
source .venv/bin/activate  # macOS/Linux
uv pip install -e .
```

</details>

## 🏗️ Project Structure

```
ticktick-mcp/
├── .env.template           # Environment variables template
├── README.md              # This file
├── requirements.txt       # Python dependencies
├── setup.py              # Package setup
├── test_server.py         # Connection test script
└── ticktick_mcp/          # Main package
    ├── __init__.py
    ├── authenticate.py    # OAuth authentication utility
    ├── cli.py            # Command-line interface
    └── src/              # Source code
        ├── __init__.py
        ├── auth.py       # OAuth implementation
        ├── server.py     # MCP server implementation
        └── ticktick_client.py  # TickTick API client
```

## 📊 What's New in v2.0

- **🌍 Enhanced Timezone Support** - Smart detection + manual override
- **⚡ Batch Operations** - Process multiple tasks simultaneously
- **🔍 Advanced Search** - Find tasks across projects with filters
- **📊 Analytics Dashboard** - Project statistics and productivity insights
- **📅 Smart Scheduling** - Today's tasks, upcoming deadlines, overdue tracking
- **🔄 Improved Error Handling** - Better user feedback and recovery
- **🚀 Performance Optimizations** - Faster task processing and API calls

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [Model Context Protocol](https://modelcontextprotocol.io/) for the amazing protocol
- [TickTick](https://ticktick.com/) for the robust API
- [Claude](https://claude.ai/) for the powerful AI integration
- All contributors and users who made this project better

---

<div align="center">

**Made with ❤️ by [Jaesung Park](https://github.com/parkjs814) & [Ilya P](https://github.com/RaiconY)**

[⭐ Star this repo](https://github.com/jacepark12/ticktick-mcp) | [🐛 Report Bug](https://github.com/jacepark12/ticktick-mcp/issues) | [💡 Request Feature](https://github.com/jacepark12/ticktick-mcp/issues)

</div>
