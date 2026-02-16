import os
import time
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from flask import Response

# ---------------------------------------------------------
# 1. CORE PIPELINE METRICS
# ---------------------------------------------------------

# Total count of generations, labeled by preset and success
ARTIFACT_GENERATION_TOTAL = Counter(
    'pegasus_artifact_generation_total',
    'Total number of artifact generation attempts',
    ['preset_id', 'status', 'provider']
)

# ---------------------------------------------------------
# 2. GEMINI 3 "THINKING" METRICS
# ---------------------------------------------------------

# Reasoning models have high latency (10s - 60s+). 
# Custom buckets help track the long-tail behavior of "Thinking"
THINKING_LATENCY = Histogram(
    'pegasus_llm_thinking_duration_seconds',
    'Time spent in the "Thinking" reasoning chain',
    ['preset_id', 'model'],
    buckets=[1.0, 5.0, 10.0, 20.0, 30.0, 45.0, 60.0, 120.0, 300.0]
)

# Track specific failures related to reasoning (e.g., Thought Signature loss)
THINKING_ERRORS = Counter(
    'pegasus_llm_thinking_errors_total',
    'Failures specifically occurring during reasoning-enabled calls',
    ['error_type', 'model']
)

# ---------------------------------------------------------
# 3. HELPER FUNCTIONS & EXPOSURE
# ---------------------------------------------------------

def setup_observability(app):
    """
    Attaches the /metrics endpoint for Prometheus scraping.
    Ensure this is called in your main backend app initialization.
    """
    @app.route('/metrics')
    def metrics():
        return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)

def track_thinking_time(preset_id: str, model: str):
    """
    Context manager or decorator to wrap LLM calls.
    Usage:
        with track_thinking_time(preset_id, model):
            response = generative_model.generate_content(...)
    """
    class ThinkingTimer:
        def __enter__(self):
            self.start = time.perf_counter()
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            duration = time.perf_counter() - self.start
            status = "success" if exc_type is None else "error"
            
            THINKING_LATENCY.labels(preset_id=preset_id, model=model).observe(duration)
            ARTIFACT_GENERATION_TOTAL.labels(
                preset_id=preset_id, 
                status=status, 
                provider="vertex"
            ).inc()
            
            if exc_type is not None:
                THINKING_ERRORS.labels(
                    error_type=exc_type.__name__, 
                    model=model
                ).inc()

    return ThinkingTimer()
