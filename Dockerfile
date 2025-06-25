FROM python:3.10-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

COPY requirements.txt .
RUN uv pip install -r requirements.txt --system

# Copy the application
COPY . .

# Install the package in development mode
RUN uv pip install -e . --system

# Expose the default SSE port
EXPOSE 3434

# Environment variables for TickTick API credentials
# These can be overridden at runtime using -e or docker-compose
ENV TICKTICK_CLIENT_ID=""
ENV TICKTICK_CLIENT_SECRET=""
ENV TICKTICK_ACCESS_TOKEN=""
ENV TICKTICK_REFRESH_TOKEN=""

# Set the default command (can be overridden)
CMD ["uv", "run", "-m", "ticktick_mcp.cli", "run", "--transport", "sse", "--host", "0.0.0.0", "--port", "3434"]