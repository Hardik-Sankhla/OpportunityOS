FROM python:3.12-slim

# Add non-root user
RUN useradd -m appuser

WORKDIR /app

# The bot depends on scheduler schemas and db client, so it shares the same requirements
COPY scheduler/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy bot code and necessary scheduler modules
COPY bot/ ./bot/
COPY scheduler/ ./scheduler/

# Change ownership to non-root user
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Only one process per container
CMD ["python", "bot/bot.py"]
