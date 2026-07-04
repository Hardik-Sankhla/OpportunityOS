FROM python:3.13-slim

# Install Supercronic (cron designed for containers)
ENV SUPERCRONIC_URL=https://github.com/aptible/supercronic/releases/download/v0.2.29/supercronic-linux-amd64
ENV SUPERCRONIC=supercronic-linux-amd64
ENV SUPERCRONIC_SHA1SUM=cd48d45c4b10f3f0bfdd3a50d0d8bb03b137452d

RUN apt-get update && apt-get install -y curl \
    && curl -fsSLO "$SUPERCRONIC_URL" \
    && echo "${SUPERCRONIC_SHA1SUM}  ${SUPERCRONIC}" | sha1sum -c - \
    && chmod +x "$SUPERCRONIC" \
    && mv "$SUPERCRONIC" "/usr/local/bin/${SUPERCRONIC}" \
    && ln -s "/usr/local/bin/${SUPERCRONIC}" /usr/local/bin/supercronic \
    && apt-get remove -y curl \
    && apt-get autoremove -y \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Add non-root user
RUN useradd -m appuser

WORKDIR /app

# Install Python requirements
COPY scheduler/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy scheduler code
COPY scheduler/ ./scheduler/

# Create a crontab file to run the pipeline periodically
# We'll run it every 6 hours by default. Supercronic will read this.
RUN echo "0 */6 * * * python /app/scheduler/run_pipeline.py" > /app/crontab

# Change ownership to non-root user
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Only one process per container
CMD ["supercronic", "/app/crontab"]
