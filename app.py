import base64
import io
from datetime import datetime, timezone, timedelta

import matplotlib
matplotlib.use("Agg")  # Headless rendering
import matplotlib.pyplot as plt
import requests
from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app = FastAPI()

# INGV FDSN event service: wider Europe box (Italy-focused but includes surrounding region) last 7 days
_start = (datetime.utcnow() - timedelta(days=7)).strftime("%Y-%m-%d")
_end = datetime.utcnow().strftime("%Y-%m-%d")
USGS_URL = (
    "https://webservices.ingv.it/fdsnws/event/1/query?format=geojson&minlatitude=35&maxlatitude=55&minlongitude=-10&maxlongitude=20"
    f"&starttime={_start}&endtime={_end}&minmagnitude=0&orderby=time"
)

# Note: start/end cover last 7 days up to now (UTC).


def fetch_earthquakes():
    items = []
    try:
        r = requests.get(USGS_URL, timeout=15)
        r.raise_for_status()
        data = r.json()
        for f in data.get("features", []):
            props = f.get("properties", {})
            mag = props.get("mag")
            t_ms = props.get("time")
            if mag is None or t_ms is None:
                continue
            t = datetime.fromtimestamp(t_ms / 1000.0, timezone.utc)
            items.append((t, mag))
    except Exception:
        # Keep items empty to trigger fallback
        pass
    # Fallback: if region returns no events (or failed), pull global weekly feed
    if not items:
        global_url = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_week.geojson"
        try:
            rg = requests.get(global_url, timeout=15)
            rg.raise_for_status()
            gdata = rg.json()
            for f in gdata.get("features", []):
                props = f.get("properties", {})
                mag = props.get("mag")
                t_ms = props.get("time")
                if mag is None or t_ms is None:
                    continue
                t = datetime.fromtimestamp(t_ms / 1000.0, timezone.utc)
                items.append((t, mag))
        except Exception:
            pass
    items.sort(key=lambda x: x[0])
    return items


def render_plot_png() -> bytes:
    items = fetch_earthquakes()
    if not items:
        fig, ax = plt.subplots(figsize=(8, 4))
        ax.text(0.5, 0.5, "No data available", ha="center", va="center", fontsize=14)
        ax.axis("off")
        buf = io.BytesIO()
        fig.tight_layout()
        fig.savefig(buf, format="png", dpi=150)
        plt.close(fig)
        return buf.getvalue()

    times = [t for t, _ in items]
    mags = [m for _, m in items]

    fig, axes = plt.subplots(1, 2, figsize=(12, 4))

    # Scatter: magnitude over time
    sizes = [max(10, (m or 0) ** 2) for m in mags]
    sc = axes[0].scatter(
        times,
        mags,
        s=sizes,
        c=mags,
        cmap="plasma",
        alpha=0.7,
        edgecolor="k",
        linewidths=0.2,
    )
    axes[0].set_title("Magnitude over time (UTC)")
    axes[0].set_xlabel("Time (UTC)")
    axes[0].set_ylabel("Magnitude")
    axes[0].grid(True, alpha=0.3)

    # Histogram: magnitude distribution
    axes[1].hist([m for m in mags if m is not None], bins=20, color="#4e79a7", edgecolor="white")
    axes[1].set_title("Magnitude distribution (INGV Europe box)")
    axes[1].set_xlabel("Magnitude")
    axes[1].set_ylabel("Count")

    fig.autofmt_xdate()
    fig.suptitle("Earthquakes in Europe box (INGV, last 7 days)", y=0.98, fontsize=12)
    fig.tight_layout(rect=(0, 0, 1, 0.95))

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150)
    plt.close(fig)
    return buf.getvalue()


@app.get("/", response_class=HTMLResponse)
def index():
    png = render_plot_png()
    b64 = base64.b64encode(png).decode("ascii")
    # Local fetch time (system local timezone)
    fetch_local = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    html = f"""
    <html>
      <head>
        <title>European Earthquakes (INGV) - Matplotlib</title>
        <meta name=viewport content="width=device-width, initial-scale=1" />
        <meta http-equiv="refresh" content="300" />
      </head>
      <body style="font-family: system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial; padding: 16px;">
        <h1 style="margin-top:0">European Earthquakes (INGV)</h1>
        <p>Data source: <a href="{USGS_URL}">INGV FDSN API (Europe box, last 7 days)</a>.</p>
        <p style=font-size:0.9em;color:#555;>Fetched locally at: {fetch_local}</p>
        <img src="data:image/png;base64,{b64}" style="max-width:100%; height:auto; border:1px solid #ccc; box-shadow: 0 1px 4px rgba(0,0,0,.1)" />
        <p style="margin-top:12px;font-size:0.9em;"><a href="https://github.com/domibies/eu-shake-map">GitHub repository</a></p>
      </body>
    </html>
    """
    return html


@app.get("/healthz")
def healthz():
    return {"ok": True}


if __name__ == "__main__":
    import threading
    import time
    import webbrowser
    import uvicorn

    url = "http://127.0.0.1:8000/"

    def _open_when_ready():
        # Try to wait for the server to become ready, then open the browser
        import requests as _r

        for _ in range(50):
            try:
                _r.get("http://127.0.0.1:8000/healthz", timeout=0.5)
                break
            except Exception:
                time.sleep(0.2)
        try:
            webbrowser.open(url)
        except Exception:
            pass

    threading.Thread(target=_open_when_ready, daemon=True).start()
    uvicorn.run(app, host="127.0.0.1", port=8000)
