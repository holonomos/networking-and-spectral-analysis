# src/netwatch/dc_controller.py
"""
Datacenter Controller - aggregates health reports from rack controllers.

Receives JSON health reports via TCP from each rack controller,
computes datacenter-wide health, and logs summaries.
"""

import json
import socket
import threading
import time
from dataclasses import dataclass, field
from typing import Dict

from netwatch.config import DCControllerConfig
from netwatch.logging_utils import get_logger
from netwatch.fft_utils import compute_dc_health_score

logger = get_logger("dc_controller")


# Health classification thresholds for datacenter
DC_THRESHOLD_HEALTHY = 0.8
DC_THRESHOLD_DEGRADED = 0.5


@dataclass
class RackReport:
    """Latest health report from a rack controller."""
    rack_id: int
    health_score: float
    server_count: int
    timestamp: float


@dataclass
class DCController:
    """Datacenter controller that aggregates rack health reports."""
    cfg: DCControllerConfig
    rack_reports: Dict[int, RackReport] = field(default_factory=dict)
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def handle_client(self, conn: socket.socket, addr: tuple) -> None:
        """Handle incoming connection from a rack controller."""
        try:
            data = b""
            while True:
                chunk = conn.recv(4096)
                if not chunk:
                    break
                data += chunk
                # Process complete JSON messages (newline-delimited)
                while b"\n" in data:
                    line, data = data.split(b"\n", 1)
                    if line.strip():
                        self._process_report(line.decode("utf-8"))
        except Exception as e:
            logger.warning("Error handling client %s: %s", addr, e)
        finally:
            conn.close()

    def _process_report(self, json_str: str) -> None:
        """Process a JSON health report from a rack controller."""
        try:
            payload = json.loads(json_str)
            report = RackReport(
                rack_id=int(payload["rack_id"]),
                health_score=float(payload["health_score"]),
                server_count=int(payload.get("server_count", 0)),
                timestamp=float(payload.get("timestamp", time.time())),
            )
            with self._lock:
                self.rack_reports[report.rack_id] = report
            logger.info(
                "Received report: rack=%d health_score=%.3f servers=%d",
                report.rack_id,
                report.health_score,
                report.server_count,
            )
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.warning("Invalid report: %s - %s", json_str[:100], e)

    def run_tcp_server(self) -> None:
        """Run TCP server to receive rack health reports."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((self.cfg.tcp_listen_host, self.cfg.tcp_listen_port))
        sock.listen(self.cfg.num_racks + 5)
        logger.info(
            "DC %d listening on %s:%d",
            self.cfg.dc_id,
            self.cfg.tcp_listen_host,
            self.cfg.tcp_listen_port,
        )

        while True:
            conn, addr = sock.accept()
            t = threading.Thread(
                target=self.handle_client, args=(conn, addr), daemon=True
            )
            t.start()

    def classify_dc_health(self, score: float) -> str:
        """Classify datacenter health based on score."""
        if score >= DC_THRESHOLD_HEALTHY:
            return "healthy"
        elif score >= DC_THRESHOLD_DEGRADED:
            return "degraded"
        else:
            return "critical"

    def run_summary_loop(self, interval_sec: float = 10.0) -> None:
        """Periodically log datacenter health summary."""
        while True:
            time.sleep(interval_sec)
            with self._lock:
                if not self.rack_reports:
                    logger.info("DC %d: No rack reports yet", self.cfg.dc_id)
                    continue

                logger.info(
                    "======== DC %d summary (%d/%d racks reporting) ========",
                    self.cfg.dc_id,
                    len(self.rack_reports),
                    self.cfg.num_racks,
                )

                rack_scores = []
                for rack_id in sorted(self.rack_reports.keys()):
                    report = self.rack_reports[rack_id]
                    age = time.time() - report.timestamp
                    logger.info(
                        "  rack=%d health=%.3f servers=%d age=%.1fs",
                        report.rack_id,
                        report.health_score,
                        report.server_count,
                        age,
                    )
                    # Only include recent reports (< 30s old)
                    if age < 30.0:
                        rack_scores.append(report.health_score)

                if rack_scores:
                    dc_score = compute_dc_health_score(rack_scores)
                    dc_health = self.classify_dc_health(dc_score)
                    logger.info(
                        "DC %d health_score=%.3f status=%s",
                        self.cfg.dc_id,
                        dc_score,
                        dc_health,
                    )
                else:
                    logger.warning("DC %d: All rack reports are stale", self.cfg.dc_id)


def main() -> None:
    cfg = DCControllerConfig.from_env()
    controller = DCController(cfg=cfg)

    # Start TCP server in background
    t = threading.Thread(
        target=controller.run_tcp_server, name="tcp_server", daemon=True
    )
    t.start()

    # Run summary loop in main thread
    controller.run_summary_loop(interval_sec=10.0)


if __name__ == "__main__":
    main()
