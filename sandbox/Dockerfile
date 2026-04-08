FROM python:3.12-slim
WORKDIR /app
COPY . .
# Simply install the project in editable mode, avoiding build/packaging issues
RUN pip install uv && uv pip install -e ".[test,dev]" --system
CMD ["python", "app/main.py"]
