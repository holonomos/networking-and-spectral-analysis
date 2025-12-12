import os
from dataclasses import dataclass

def getenv_int(name: str, default: int) -> int:
    v = os.getenv(name)
    return int(v) if v is not None else default

def getenv_float(name: str, default: float) -> float:
    v = os.getenv(name)
    return float(v) if v is not None else default

def getenv_str(name: str, default: str) -> str:
    v = os.getenv(name)
    return v if v is not None else default


@dataclass
class ServerConfig:
    rack_id: int
    server_id: int
    rack_controller_host: str
    rack_controller_port: int
    interval_sec: float

    @classmethod
    def from_env(cls) -> "ServerConfig":
        return cls(
            rack_id=getenv_int("RACK_ID", 0),
            server_id=getenv_int("SERVER_ID", 0),
            rack_controller_host=getenv_str("RACK_CONTROLLER_HOST", "127.0.0.1"),
            rack_controller_port=getenv_int("RACK_CONTROLLER_PORT", 9999),
            interval_sec=getenv_float("INTERVAL_SEC", 0.05),
        )


@dataclass
class RackControllerConfig:
    rack_id: int
    udp_listen_host: str
    udp_listen_port: int
    dc_controller_host: str
    dc_controller_port: int
    metrics_port: int

    @classmethod
    def from_env(cls) -> "RackControllerConfig":
        return cls(
            rack_id=getenv_int("RACK_ID", 0),
            udp_listen_host=getenv_str("UDP_LISTEN_HOST", "0.0.0.0"),
            udp_listen_port=getenv_int("UDP_LISTEN_PORT", 9999),
            dc_controller_host=getenv_str("DC_CONTROLLER_HOST", "127.0.0.1"),
            dc_controller_port=getenv_int("DC_CONTROLLER_PORT", 9990),
            metrics_port=getenv_int("METRICS_PORT", 8000),
        )


@dataclass
class DCControllerConfig:
    dc_id: int
    tcp_listen_host: str
    tcp_listen_port: int
    num_racks: int
    metrics_port: int

    @classmethod
    def from_env(cls) -> "DCControllerConfig":
        return cls(
            dc_id=getenv_int("DC_ID", 0),
            tcp_listen_host=getenv_str("TCP_LISTEN_HOST", "0.0.0.0"),
            tcp_listen_port=getenv_int("TCP_LISTEN_PORT", 9990),
            num_racks=getenv_int("NUM_RACKS", 4),
            metrics_port=getenv_int("METRICS_PORT", 8000),
        )
