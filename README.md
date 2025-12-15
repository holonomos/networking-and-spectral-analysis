# NetWatch 🔬

**Spectral analysis-based network health monitoring** — detecting infrastructure anomalies using signal processing, not just packet counting.

[![Python](https://img.shields.io/badge/Python-3.12-blue.svg)](https://python.org)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED.svg)](https://docs.docker.com/compose/)
[![Kubernetes](https://img.shields.io/badge/Kubernetes-Ready-326CE5.svg)](https://kubernetes.io/)
[![Prometheus](https://img.shields.io/badge/Prometheus-Metrics-E6522C.svg)](https://prometheus.io/)
[![Grafana](https://img.shields.io/badge/Grafana-Dashboards-F46800.svg)](https://grafana.com/)

---

## The Idea

Traditional monitoring counts packets and measures latency. **NetWatch treats network health as a signal processing problem:**

1. Each server emits a **unique sinusoidal signal** (like radio stations on different frequencies)
2. Controllers perform **FFT analysis** on received samples
3. **Signal degradation = health problems** — packet loss, delays, or failures corrupt spectral purity
4. Health is quantified using **Signal-to-Noise Ratio (SNR)** and **spectral error**

> *Pure signal = healthy server. Noisy spectrum = troubled server.*

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        DATACENTER                                │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                    DC Controller                          │   │
│  │                  (TCP Aggregation)                        │   │
│  │              Computes DC-wide health score                │   │
│  └─────────────────────▲────────────────────────────────────┘   │
│                        │ TCP Health Reports                      │
│   ┌────────────────────┼────────────────────────────────────┐   │
│   │                    │                                     │   │
│  ┌▼──────────┐  ┌──────▼───┐  ┌───────────┐  ┌───────────┐  │   │
│  │   Rack 0   │  │  Rack 1  │  │  Rack 2   │  │  Rack 3   │  │   │
│  │ Controller │  │Controller│  │ Controller│  │ Controller│  │   │
│  │  (FFT +    │  │          │  │           │  │           │  │   │
│  │  Metrics)  │  │          │  │           │  │           │  │   │
│  └─────▲──────┘  └────▲─────┘  └─────▲─────┘  └─────▲─────┘  │   │
│        │ UDP          │ UDP          │ UDP          │ UDP    │   │
│   ┌────┴────┐    ┌────┴────┐    ┌────┴────┐    ┌────┴────┐   │   │
│   │ 8 Servers│   │ 8 Servers│   │ 8 Servers│   │ 8 Servers│  │   │
│   │ 1.0-1.35Hz│  │ 2.0-2.35Hz│  │ 3.0-3.35Hz│  │ 4.0-4.35Hz│ │   │
│   └──────────┘   └──────────┘   └──────────┘   └──────────┘  │   │
│                                                               │   │
└───────────────────────────────────────────────────────────────┘   │
                                                                     │
      ┌─────────────┐              ┌─────────────┐                  │
      │ Prometheus  │─────────────▶│   Grafana   │                  │
      │  (Scrapes)  │              │ (Dashboards)│                  │
      └─────────────┘              └─────────────┘                  │
```

**37 containers:** 1 DC Controller, 4 Rack Controllers, 32 Servers, Prometheus, Grafana

---

## Key Features

| Feature | Description |
|---------|-------------|
| **FFT-Based Health Detection** | Applies Hanning window + FFT to detect signal corruption |
| **Hierarchical Monitoring** | Three-tier aggregation: Server → Rack → Datacenter |
| **Real-Time Spectral Metrics** | SNR (dB), spectral error, packet loss, latency histograms |
| **Prometheus + Grafana** | Full observability stack with pre-built dashboards |
| **Chaos Engineering** | Built-in fault injection using `tc netem` |
| **Dual Deployment** | Docker Compose (local) and Kubernetes (production) |

---

## Health Classification

| Spectral Error | Status | Meaning |
|---------------|--------|---------|
| < 0.2 | ✅ Healthy | Clean signal at expected frequency |
| 0.2 - 0.5 | ⚠️ Warning | Degraded signal quality |
| > 0.5 | 🔴 Critical | Signal dominated by noise |

---

## Quick Start

```bash
# Clone and run
git clone https://github.com/YOUR_USERNAME/netwatch.git
cd netwatch
docker-compose up --build

# Access dashboards
# Grafana:    http://localhost:3000  (admin/admin)
# Prometheus: http://localhost:9095
```

### Inject Chaos (Kubernetes)
```bash
# Add 200ms delay + 20% packet loss to rack 0
python chaos/chaos_injector.py --rack 0 --delay 200ms --loss 20

# Clear chaos
python chaos/chaos_injector.py --rack 0 --clear
```

---

## Tech Stack

- **Python 3.12** — Core logic with NumPy for FFT
- **Docker Compose** — Local development and testing
- **Kubernetes** — Production deployment manifests
- **Prometheus** — Metrics collection (2s scrape interval)
- **Grafana** — Pre-provisioned dashboards
- **tc netem** — Network chaos injection

---

## Metrics Exposed

```promql
# Server-level
netwatch_server_spectral_error{rack_id, server_id}  # 0=healthy, 1=noise
netwatch_server_snr_db{rack_id, server_id}          # Signal-to-Noise in dB

# Rack-level  
netwatch_rack_health_score{rack_id}                 # Aggregated health

# Datacenter-level
netwatch_dc_health_score{dc_id}                     # Overall health

# Operational
netwatch_packets_received_total{rack_id, server_id}
netwatch_packets_lost_total{rack_id, server_id}
netwatch_latency_ms{rack_id, server_id}             # Histogram
```

---

## Project Structure

```
netwatch/
├── src/netwatch/           # Core Python modules
│   ├── server_agent.py     # Sinusoidal wave generator + UDP sender
│   ├── rack_controller.py  # UDP receiver + FFT analysis + metrics
│   ├── dc_controller.py    # TCP aggregator for rack reports
│   ├── fft_utils.py        # Signal processing (FFT, SNR, classification)
│   └── metrics_utils.py    # Prometheus metric definitions
├── containers/             # Dockerfiles for each component
├── chaos/                  # Fault injection tooling
├── grafana/                # Dashboard JSON + provisioning
├── prometheus/             # Scrape configuration
├── k8s/                    # Kubernetes manifests
└── docker-compose.yml      # Full stack (37 containers)
```

---

## Why This Approach?

| Traditional Monitoring | NetWatch |
|------------------------|----------|
| Counts packets | Analyzes signal spectrum |
| Binary health (up/down) | Continuous health score (0-1) |
| Threshold-based alerts | Spectral anomaly detection |
| Per-metric analysis | Holistic signal quality |

The spectral approach detects **subtle degradation patterns** that packet counting would miss—intermittent failures, clock drift, and periodic network issues all appear as spectral anomalies.

---

## License

MIT
