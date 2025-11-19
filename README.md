# eu-shake-map

Hello-world FastAPI service that fetches recent earthquakes (INGV with USGS fallback) and renders a simple Matplotlib chart. Designed as a compact, portable demo for multi-arch Docker builds (Linux, macOS, Windows).

Quick start
- Local:
  ```
  uv run python app.py
  ```
  Then open http://127.0.0.1:8000/
- Docker:
  ```
  docker build -t eu-shake-map:dev .
  docker run --rm -p 8000:8000 eu-shake-map:dev
  ```

Endpoints
- /        HTML page with embedded PNG chart
- /healthz Health check endpoint
