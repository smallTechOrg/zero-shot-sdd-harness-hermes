FROM python:3.11-slim

WORKDIR /app

# Install uv
RUN pip install uv

# Copy project dependencies
COPY pyproject.toml uv.lock ./

# Install dependencies using uv
RUN uv sync --frozen

# Copy source code
COPY . .

EXPOSE 8000

CMD ["uv", "run", "python", "-m", "src"]
