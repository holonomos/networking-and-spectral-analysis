# src/netwatch/metrics_utils.py
"""
Prometheus metrics utilities for NetWatch.

Provides gauges, counters, and histograms for monitoring:
- Server-level spectral errors and health
- Rack-level health scores
- Datacenter-level health scores
- Packet counts and latencies
"""

from prometheus_client import Counter, Gauge, Histogram, start_http_server
from typing import Optional

# Gauges for health metrics
SERVER_SPECTRAL_ERROR = Gauge(
    "netwatch_server_spectral_error",
    "Spectral error for a server (0=healthy, 1=noise)",
    ["rack_id", "server_id"],
)

SERVER_SNR = Gauge(
    "netwatch_server_snr_db",
    "Signal-to-noise ratio in dB for a server",
    ["rack_id", "server_id"],
)

RACK_HEALTH_SCORE = Gauge(
    "netwatch_rack_health_score",
    "Health score for a rack (0=failed, 1=healthy)",
    ["rack_id"],
)

DC_HEALTH_SCORE = Gauge(
    "netwatch_dc_health_score",
    "Health score for a datacenter (0=failed, 1=healthy)",
    ["dc_id"],
)

# Counters for packet tracking
PACKETS_RECEIVED = Counter(
    "netwatch_packets_received_total",
    "Total packets received from servers",
    ["rack_id", "server_id"],
)

PACKETS_LOST = Counter(
    "netwatch_packets_lost_total",
    "Total packets lost from servers",
    ["rack_id", "server_id"],
)

# Histogram for latencies
LATENCY_HISTOGRAM = Histogram(
    "netwatch_latency_ms",
    "Packet latency in milliseconds",
    ["rack_id", "server_id"],
    buckets=[1, 5, 10, 25, 50, 100, 250, 500, 1000],
)


class MetricsRegistry:
    """Helper class to manage metrics updates."""

    _server_started: bool = False

    @classmethod
    def start_server(cls, port: int = 8000) -> None:
        """Start the Prometheus metrics HTTP server."""
        if not cls._server_started:
            start_http_server(port)
            cls._server_started = True

    @staticmethod
    def update_server_metrics(
        rack_id: int,
        server_id: int,
        spectral_error: float,
        snr_db: float,
        packets_received: int = 0,
        packets_lost: int = 0,
        latency_ms: Optional[float] = None,
    ) -> None:
        """Update metrics for a specific server."""
        labels = {"rack_id": str(rack_id), "server_id": str(server_id)}
        SERVER_SPECTRAL_ERROR.labels(**labels).set(spectral_error)
        SERVER_SNR.labels(**labels).set(snr_db)

        if packets_received > 0:
            PACKETS_RECEIVED.labels(**labels).inc(packets_received)
        if packets_lost > 0:
            PACKETS_LOST.labels(**labels).inc(packets_lost)
        if latency_ms is not None:
            LATENCY_HISTOGRAM.labels(**labels).observe(latency_ms)

    @staticmethod
    def update_rack_health(rack_id: int, health_score: float) -> None:
        """Update health score for a rack."""
        RACK_HEALTH_SCORE.labels(rack_id=str(rack_id)).set(health_score)

    @staticmethod
    def update_dc_health(dc_id: int, health_score: float) -> None:
        """Update health score for a datacenter."""
        DC_HEALTH_SCORE.labels(dc_id=str(dc_id)).set(health_score)
