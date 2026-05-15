FROM python:3.12-slim

WORKDIR /app

COPY mcp-server/pyproject.toml mcp-server/server.py ./
RUN pip install --no-cache-dir .

# Skills directory is mounted at runtime
ENV SKILLS_DIR=/skills

ENTRYPOINT ["skills-mcp-server"]
