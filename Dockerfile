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

# Create startup scripts for different modes
RUN echo '#!/bin/sh\n\
    uv run -m ticktick_mcp.cli auth\n\
    uv run -m ticktick_mcp.cli run --transport streamable-http --host 0.0.0.0 --port 8000\n\
    ' > /usr/local/bin/run-with-auth && \
    chmod +x /usr/local/bin/run-with-auth

RUN echo '#!/bin/sh\n\
    uv run -m ticktick_mcp.cli run --transport streamable-http --host 0.0.0.0 --port 8000\n\
    ' > /usr/local/bin/run-production && \
    chmod +x /usr/local/bin/run-production

# Expose the default FastMCP HTTP port
EXPOSE 8000

# Default: Run with authentication flow for interactive setup
CMD ["/bin/sh", "-c", "run-production"]
