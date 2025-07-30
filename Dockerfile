# Dockerfile for TickTick MCP Server (FastMCP, streamable-http)
FROM python:3.10-slim

# Install uv and copy project files
RUN pip install uv
COPY . /app
WORKDIR /app

# Create a virtual environment
RUN uv venv .

# Install dependencies using uv
RUN uv pip install -e .

# Expose the default FastMCP HTTP port
EXPOSE 8000

# Start the MCP server with streamable-http transport (default host/port)
CMD ["uv", "run", "-m", "ticktick_mcp.cli", "run", "--transport", "streamable-http", "--host", "0.0.0.0", "--port", "8000"]
