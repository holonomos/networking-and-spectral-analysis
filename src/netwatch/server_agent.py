import json
import math
import socket
import time
from typing import Tuple

from netwatch.config import ServerConfig
from netwatch.logging_utils import get_logger

logger = get_logger("server_agent")

def compute_server_frequency(rack_id: int, server_id: int) -> float:
    """
    Base frequency per rack + small offset per server.
    rack 0 -> 1Hz, rack 1 -> 2Hz, etc.; delta = 0.05Hz per server.
    """
    base_freq = 1.0 + rack_id  # 0->1Hz, 1->2Hz, 2->3Hz, 3->4Hz
    delta = 0.05
    return base_freq + delta * server_id


def generate_wave_sample(freq_hz: float, t: float, amplitude: float = 1.0) -> float:
    """
    Generate a sinusoidal wave sample: A * sin(2π * f * t)
    """
    return amplitude * math.sin(2 * math.pi * freq_hz * t)


def main() -> None:
    cfg = ServerConfig.from_env()
    logger.info(
        "Starting server agent rack_id=%d server_id=%d -> %s:%d interval=%.3fs",
        cfg.rack_id,
        cfg.server_id,
        cfg.rack_controller_host,
        cfg.rack_controller_port,
        cfg.interval_sec,
    )

    freq_hz = compute_server_frequency(cfg.rack_id, cfg.server_id)
    logger.info("Using frequency %.3f Hz", freq_hz)

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    target: Tuple[str, int] = (cfg.rack_controller_host, cfg.rack_controller_port)

    seq = 0
    start = time.time()

    try:
        while True:
            now = time.time()
            t = now - start
            wave_sample = generate_wave_sample(freq_hz, t)

            payload = {
                "rack_id": cfg.rack_id,
                "server_id": cfg.server_id,
                "seq": seq,
                "sent_ts": now,
                "wave_sample": wave_sample,
            }

            sock.sendto(json.dumps(payload).encode("utf-8"), target)
            if seq % 100 == 0:
                logger.info("Sent seq=%d wave_sample=%.4f t=%.3f", seq, wave_sample, t)
            seq += 1
            time.sleep(cfg.interval_sec)
    except KeyboardInterrupt:
        logger.info("Server agent exiting")
if __name__ == "__main__":
    main()
