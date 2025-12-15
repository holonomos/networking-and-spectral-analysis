# NetWatch: The Pulse of the Machine

> "In the deafening silence of a data center, every server is singing. You just need to know how to listen."

## The Philosophy: Signal Over Statistics

Most network monitoring tools are accountants. They count packets. They tally errors. They measure latency in milliseconds and call it a day. If the ping works, the network is "up." If the packet count matches, the network is "healthy."

**NetWatch is not an accountant. NetWatch is a cardiologist.**

It operates on a fundamental truth that traditional monitoring ignores: **Network health is a signal processing problem.**

When a network jitters, when a switch buffer fills, when a clock drifts—the "flow" of data changes texture. A simple ping won't catch the subtle arrhythmia of a struggling microservice, but a spectral analysis will. NetWatch doesn't ask "Did it arrive?"; it asks "How pure was the arrival?"

---

## The Symphony: Anatomy of a Heartbeat

At the edge of the network, deep in the `server_agent.py`, 32 containers are doing something unusual. They aren't serving web pages. They aren't crunching numbers.

**They are singing.**

Each server generates a continuous, perfect sine wave:
$$ y(t) = A \cdot \sin(2\pi f t) $$

But here is the elegance: **Every server has its own frequency.**
- Rack 0, Server 0 sings at **1.00 Hz**.
- Rack 0, Server 1 sings at **1.05 Hz**.
- ...
- Rack 3, Server 7 sings at **4.35 Hz**.

This isn't chaos; it's an orchestra. Each server transmits its song via UDP packets at a precise 20 Hz sample rate. These aren't just keep-alives; they are high-fidelity audio samples of the server's existence.

---

## The Ear: Fast Fourier Transform (FFT)

The **Rack Controller** (`rack_controller.py`) is the listener. It sits on the network, collecting these UDP samples into a rolling buffer.

But it doesn't just read the numbers. It applies the **Fast Fourier Transform (FFT)**.

In `fft_utils.py`, the magic happens. The controller takes the time-domain signal (the jagged, messy arrival of packets) and transforms it into the frequency domain.

### The Perfect Hanning Window
Before the FFT, we apply a **Hanning Window**. Why? Because in the real world, signals don't stop and start perfectly. The Hanning window smooths the edges, reducing "spectral leakage"—the mathematical artifact that makes a clean signal look messy. It’s the difference between a blurred photo and a sharp portrait.

### SNR: The Truth Teller
Once in the frequency domain, we look for the specific frequency that server is *supposed* to be singing.
- **Signal Power**: The energy at exactly 1.05 Hz (for R0-S1).
- **Noise Power**: The energy *everywhere else*.

Then we calculate the **Signal-to-Noise Ratio (SNR)**.

$$ \text{SNR}_{dB} = 10 \cdot \log_{10} \left( \frac{\text{Signal Power}}{\text{Noise Power}} \right) $$

If a network switch delays a packet by 10ms, the perfect sine wave gets distorted. The energy "leaks" from the pure frequency into the noise floor. **The SNR drops.** The `spectral_error` rises.

We don't need to know *why* the network is failing to know *that* it is failing. The physics of the signal tells us everything.

---

## The Diagnosis: Spectral Error

NetWatch condenses this complex math into a single, merciless metric: **Spectral Error**.

- **0.0 - 0.2 (Healthy)**: The server is singing a pure, unblemished note. The network is transparent.
- **0.2 - 0.5 (Warning)**: The note is wavering. There is jitter. Packets are bunching up. The "sound" is fuzzy.
- **> 0.5 (Critical)**: The signal is lost in the noise. The server might be up, but it is screaming into a void.

This allows us to detect issues that are invisible to other tools. A 5% packet loss with random distribution looks very different spectrally than a specific periodic connectivity gap. NetWatch sees the difference.

---

## The Hierarchy of Intelligence

The system is built like a nervous system:
1.  **Nerves (Server Agents)**: Generate raw sensation (Sine Waves).
2.  **Spinal Cord (Rack Controllers)**: Process sensation into reflex (FFT & Rack Health). Aggregates 8 servers.
3.  **Brain (DC Controller)**: Aggregates rack reports via TCP. It doesn't care about sine waves anymore; it cares about the *health of the racks*.

This separation of concerns ensures scalability. The DC Controller isn't overwhelmed by 20Hz samples from 32 servers. It receives calm, summarized reports from the Rack Controllers.

---

## Chaos: The Test of Resilience

We don't just hope the network works. We break it on purpose.

The `chaos` module is a first-class citizen. Using `tc netem` (Traffic Control Network Emulation), we can inject:
- **Delay**: "Add 200ms latency to Rack 0."
- **Loss**: "Drop 20% of packets from Server 3."
- **Corruption**: "Garble the bits."

You can watch in real-time on Grafana as a `loss` command executes. The pristine spectral peak of a server collapses. The noise floor rises. The SNR crashes. It is a visceral visualization of network trauma.

---

## Final Thoughts

NetWatch is what happens when you stop treating computers like calculators and start treating them like physics experiments. It is a testament to the fact that looking at the same old problem through a different lens—the lens of signal processing—can reveal hidden realities.

It is not just a monitoring tool. **It is a truth machine.**
