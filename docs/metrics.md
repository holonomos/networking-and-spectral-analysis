# NetWatch Metrics

Prometheus metrics exposed by NetWatch components.

## Server Metrics

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `netwatch_server_spectral_error` | Gauge | rack_id, server_id | Spectral error (0=healthy, 1=noise) |
| `netwatch_server_snr_db` | Gauge | rack_id, server_id | Signal-to-noise ratio in dB |
| `netwatch_packets_received_total` | Counter | rack_id, server_id | Total packets received |
| `netwatch_packets_lost_total` | Counter | rack_id, server_id | Total packets lost |
| `netwatch_latency_ms` | Histogram | rack_id, server_id | Packet latency distribution |

## Rack Metrics

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `netwatch_rack_health_score` | Gauge | rack_id | Rack health (0=failed, 1=healthy) |

## Datacenter Metrics

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `netwatch_dc_health_score` | Gauge | dc_id | DC health (0=failed, 1=healthy) |

## Latency Buckets

The `netwatch_latency_ms` histogram uses these buckets (milliseconds):
- 1, 5, 10, 25, 50, 100, 250, 500, 1000

## Example Queries

```promql
# Average spectral error across all servers in rack 0
avg(netwatch_server_spectral_error{rack_id="0"})

# Packet loss rate for a server
rate(netwatch_packets_lost_total{rack_id="0", server_id="0"}[5m]) /
rate(netwatch_packets_received_total{rack_id="0", server_id="0"}[5m])

# 99th percentile latency
histogram_quantile(0.99, rate(netwatch_latency_ms_bucket[5m]))

# Servers with critical health
netwatch_server_spectral_error > 0.5
```
