# NetWatch Architecture

NetWatch is a hierarchical network monitoring system that uses spectral analysis to detect anomalies.

## Component Hierarchy

```mermaid
graph TB
    subgraph "Datacenter"
        DC[DC Controller<br/>Port 9990]
        
        subgraph "Rack 0"
            RC0[Rack Controller 0<br/>Port 9999]
            S00[Server 0] --> RC0
            S01[Server 1] --> RC0
            S02[...] --> RC0
            S07[Server 7] --> RC0
        end
        
        subgraph "Rack 1"
            RC1[Rack Controller 1<br/>Port 10000]
            S10[Server 0] --> RC1
            S17[...] --> RC1
        end
        
        subgraph "Rack 2"
            RC2[Rack Controller 2<br/>Port 10001]
            S20[...] --> RC2
        end
        
        subgraph "Rack 3"
            RC3[Rack Controller 3<br/>Port 10002]
            S30[...] --> RC3
        end
        
        RC0 -->|TCP| DC
        RC1 -->|TCP| DC
        RC2 -->|TCP| DC
        RC3 -->|TCP| DC
    end
```

## Components

### Server Agent (`server_agent.py`)
- Generates sinusoidal wave samples at a unique frequency
- Frequency formula: `base_freq + 0.05 * server_id` where `base_freq = 1 + rack_id`
- Sends UDP packets every 50ms (20 Hz) to its rack controller
- Packet payload: `{rack_id, server_id, seq, sent_ts, wave_sample}`

### Rack Controller (`rack_controller.py`)
- Receives UDP packets from all servers in its rack
- Maintains per-server statistics: packet counts, latencies, wave buffer
- Runs FFT analysis every 5 seconds to compute spectral error
- Reports rack health score to DC Controller via TCP

### DC Controller (`dc_controller.py`)
- Receives TCP health reports from all rack controllers
- Aggregates rack scores to compute datacenter-wide health
- Logs datacenter summary every 10 seconds

## Health Scoring

### Spectral Error
Computed from FFT analysis:
- **0.0** = Pure signal at expected frequency
- **1.0** = Pure noise, no signal detected

### Health Classification
| Level | Spectral Error | Status |
|-------|---------------|--------|
| Healthy | < 0.2 | ✅ Normal |
| Sev2 | 0.2 - 0.5 | ⚠️ Warning |
| Sev1 | > 0.5 | 🔴 Critical |

### Aggregation
- **Rack Health** = `1 - avg(server_spectral_errors)`
- **DC Health** = `avg(rack_health_scores)`

## Data Flow

1. **Server → Rack Controller** (UDP, 20 Hz)
   - Wave samples, sequence numbers, timestamps

2. **Rack Controller → DC Controller** (TCP, every 5s)
   - `{rack_id, health_score, server_count, timestamp}`

3. **Logs** (stdout, every 5-10s)
   - Per-server stats, rack health, DC health
