# src/netwatch/rack_controller.py
import json
import socket
import threading
import time
import numpy as np
from collections import deque
from dataclasses import dataclass, field
from typing import Deque, Dict, List, Tuple

from netwatch.config import RackControllerConfig
from netwatch.logging_utils import get_logger
from netwatch.fft_utils import analyze_signal, classify_health, compute_rack_health_score

logger = get_logger("rack_controller")

Sample = Tuple[int, float, float, float]  # (seq, sent_ts, recv_ts, wave_sample)


@dataclass
class ServerStats:
    server_id: int
    last_seq: int = -1
    received_count: int = 0
    lost_count: int = 0
    latencies_ms: List[float] = field(default_factory=list)
    wave_buffer: Deque[float] = field(default_factory=lambda: deque(maxlen=2048))

    def record_packet(self, seq: int, sent_ts: float, recv_ts: float, wave_sample: float) -> None:
        # Packet/loss accounting
        if self.last_seq >= 0 and seq > self.last_seq + 1:
            self.lost_count += (seq - self.last_seq - 1)
        self.last_seq = seq
        self.received_count += 1

        # Latency
        latency_ms = (recv_ts - sent_ts) * 1000.0
        self.latencies_ms.append(latency_ms)
        # Keep latency history bounded
        if len(self.latencies_ms) > 1000:
            self.latencies_ms = self.latencies_ms[-1000:]

        # Wave buffer for FFT
        self.wave_buffer.append(wave_sample)

    def summarize(
        self,
        sample_rate_hz: float,
        expected_freq_hz: float,
        window_seconds: float,
        packets_in_window: int,
    ) -> Dict[str, float]:
        """
        Compute simple stats + spectral health for logging / metrics.
        """
        if self.received_count == 0:
            return {
                "received_total": 0.0,
                "lost_total": 0.0,
                "loss_rate": 0.0,
                "latency_mean_ms": 0.0,
                "latency_max_ms": 0.0,
                "arrival_rate_hz": 0.0,
                "spectral_error": 0.0,
                "spectral_snr_db": 0.0,
            }

        received_total = float(self.received_count)
        lost_total = float(self.lost_count)
        denom = received_total + lost_total if (received_total + lost_total) > 0 else 1.0
        loss_rate = lost_total / denom

        if self.latencies_ms:
            lat_mean = sum(self.latencies_ms) / len(self.latencies_ms)
            lat_max = max(self.latencies_ms)
        else:
            lat_mean = 0.0
            lat_max = 0.0

        # Arrival rate approximated by packets in last summary window
        arrival_rate_hz = packets_in_window / max(window_seconds, 1e-6)

        # Spectral health using fft_utils.analyze_signal
        if len(self.wave_buffer) >= 64:
            samples_arr = np.array(self.wave_buffer, dtype=float)
            metrics = analyze_signal(
                samples=samples_arr,
                sample_rate=sample_rate_hz,
                expected_freq=expected_freq_hz,
                bandwidth=0.1,
            )
            spectral_error = metrics.spectral_error
            snr_db = metrics.snr
        else:
            spectral_error, snr_db = 0.0, 0.0

        return {
            "received_total": received_total,
            "lost_total": lost_total,
            "loss_rate": loss_rate,
            "latency_mean_ms": lat_mean,
            "latency_max_ms": lat_max,
            "arrival_rate_hz": arrival_rate_hz,
            "spectral_error": spectral_error,
            "spectral_snr_db": snr_db,
        }


class RackController:
    def __init__(self, cfg: RackControllerConfig, sample_rate_hz: float = 20.0) -> None:
        self.cfg = cfg
        self.sample_rate_hz = sample_rate_hz
        self._lock = threading.Lock()
        self.server_stats: Dict[int, ServerStats] = {}
        # For per-window arrival rate estimates
        self._window_counts: Dict[int, int] = {}
        # TCP socket for reporting to DC Controller (lazy init)
        self._dc_socket: socket.socket | None = None

    def _get_server_stats(self, server_id: int) -> ServerStats:
        with self._lock:
            stats = self.server_stats.get(server_id)
            if stats is None:
                stats = ServerStats(server_id=server_id)
                self.server_stats[server_id] = stats
                self._window_counts[server_id] = 0
            return stats

    def _report_to_dc(self, health_score: float, server_count: int) -> None:
        """Send health report to DC Controller via TCP."""
        report = {
            "rack_id": self.cfg.rack_id,
            "health_score": health_score,
            "server_count": server_count,
            "timestamp": time.time(),
        }
        msg = json.dumps(report) + "\n"
        try:
            if self._dc_socket is None:
                self._dc_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self._dc_socket.connect(
                    (self.cfg.dc_controller_host, self.cfg.dc_controller_port)
                )
                logger.info(
                    "Connected to DC Controller at %s:%d",
                    self.cfg.dc_controller_host,
                    self.cfg.dc_controller_port,
                )
            self._dc_socket.sendall(msg.encode("utf-8"))
        except Exception as e:
            logger.warning("Failed to report to DC Controller: %s", e)
            # Reset socket for reconnection
            if self._dc_socket:
                try:
                    self._dc_socket.close()
                except Exception:
                    pass
                self._dc_socket = None

    def run_udp_listener(self) -> None:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind((self.cfg.udp_listen_host, self.cfg.udp_listen_port))
        logger.info(
            "Rack %d listening on %s:%d",
            self.cfg.rack_id,
            self.cfg.udp_listen_host,
            self.cfg.udp_listen_port,
        )

        while True:
            data, addr = sock.recvfrom(4096)
            recv_ts = time.time()
            try:
                payload = json.loads(data.decode("utf-8"))
            except json.JSONDecodeError:
                logger.warning("Invalid JSON from %s", addr)
                continue

            rack_id = int(payload.get("rack_id", -1))
            if rack_id != self.cfg.rack_id:
                logger.warning(
                    "Packet for rack_id=%s on rack_id=%d controller",
                    rack_id,
                    self.cfg.rack_id,
                )
                continue

            server_id = int(payload.get("server_id", -1))
            seq = int(payload.get("seq", -1))
            sent_ts = float(payload.get("sent_ts", 0.0))
            wave_sample = float(payload.get("wave_sample", 0.0))

            stats = self._get_server_stats(server_id)
            stats.record_packet(seq, sent_ts, recv_ts, wave_sample)

            with self._lock:
                self._window_counts[server_id] = self._window_counts.get(server_id, 0) + 1

            if seq % 100 == 0:
                logger.info(
                    "Received server_id=%d seq=%d wave=%.4f latency=%.1fms",
                    server_id,
                    seq,
                    wave_sample,
                    (recv_ts - sent_ts) * 1000.0,
                )

    def run_summary_loop(self, interval_sec: float = 5.0) -> None:
        while True:
            time.sleep(interval_sec)
            with self._lock:
                if not self.server_stats:
                    logger.info("No samples yet for rack %d", self.cfg.rack_id)
                    continue

                logger.info("======== Rack %d summary (last %.1fs) ========",
                            self.cfg.rack_id, interval_sec)
                spectral_errors = []

                for server_id, stats in self.server_stats.items():
                    # Approx expected frequency for this server
                    base_freq = 1.0 + self.cfg.rack_id
                    delta = 0.05
                    expected_freq = base_freq + delta * server_id

                    packets_in_window = self._window_counts.get(server_id, 0)
                    summary = stats.summarize(
                        sample_rate_hz=self.sample_rate_hz,
                        expected_freq_hz=expected_freq,
                        window_seconds=interval_sec,
                        packets_in_window=packets_in_window,
                    )

                    health = classify_health(summary["spectral_error"])


                    logger.info(
                        "server=%d recv_total=%.0f lost_total=%.0f loss_rate=%.3f "
                        "arrival_rate=%.1fHz lat_mean=%.1fms lat_max=%.1fms "
                        "spectral_error=%.3f snr=%.1fdB health=%s",
                        server_id,
                        summary["received_total"],
                        summary["lost_total"],
                        summary["loss_rate"],
                        summary["arrival_rate_hz"],
                        summary["latency_mean_ms"],
                        summary["latency_max_ms"],
                        summary["spectral_error"],
                        summary["spectral_snr_db"],
                        health,
                    )
                    spectral_errors.append(summary["spectral_error"])

                rack_health = compute_rack_health_score(spectral_errors)
                logger.info("Rack %d health_score=%.3f", self.cfg.rack_id, rack_health)

                # Report to DC Controller
                self._report_to_dc(rack_health, len(self.server_stats))

                # Reset window counts for next interval
                self._window_counts = {sid: 0 for sid in self._window_counts.keys()}


def main() -> None:
    cfg = RackControllerConfig.from_env()
    controller = RackController(cfg, sample_rate_hz=20.0)

    t = threading.Thread(
        target=controller.run_udp_listener, name="udp_listener", daemon=True
    )
    t.start()

    controller.run_summary_loop(interval_sec=5.0)


if __name__ == "__main__":
    main()
