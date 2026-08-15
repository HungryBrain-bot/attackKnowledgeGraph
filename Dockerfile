# attck-graph query API - see docs/decisions/007-api-and-containerization.md
# for why this is single-stage and why the STIX bundle is never fetched
# here.
#
# data/graph_with_semantics.json (the combined structural + semantic
# graph the API actually reads, via query/graph_loader.py) is a
# COMMITTED, tracked file in this repo - it is NOT built at image-build
# time and does NOT need a volume mount at runtime. Only the raw STIX
# bundle (data/raw/enterprise-attack.json, ~48MB, gitignored) and
# secrets (.env) are deliberately excluded from the image - see
# .dockerignore. If you change graph/seed_config.py or
# graph/semantic_edges.py, regenerate and commit the graph JSON files
# BEFORE rebuilding this image (see README's Quick Start /
# docs/decisions/007 - this image will not regenerate them for you).
#
# Matches the project's tested Python version (3.13, see README's
# badge / CI workflow).
FROM python:3.13-slim

WORKDIR /app

# Install dependencies first so this layer is cached across code-only
# changes.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copies the whole repo except what .dockerignore excludes (.venv/,
# .git/, data/raw/, data/test_logs/, .env, NOTES-private.md) - this DOES
# include the committed data/graph_with_semantics.json /
# data/structural_graph.json, api/, query/, graph/, etc.
COPY . .

EXPOSE 8000

# No .env is baked into the image (excluded via .dockerignore) - pass
# LLM provider credentials at run time via `docker run --env-file .env`
# or docker-compose.yml's `env_file:`. Without any credentials, the API
# still serves /health, /techniques, and /query (facts-only, per
# query/llm_provider.py's has_credentials() degradation).
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
