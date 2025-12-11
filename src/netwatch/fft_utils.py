"""
FFT-based spectral analysis utilities for NetWatch.

This module provides functions to:
1. Compute FFT on time-series wave samples
2. Calculate Signal-to-Noise Ratio (SNR)
3. Compute spectral error for anomaly detection
4. Classify server health based on spectral metrics
"""

import numpy as np
from typing import Tuple, NamedTuple


class SpectralMetrics(NamedTuple):
    """Results from spectral analysis of a signal."""
    snr: float              # Signal-to-Noise Ratio in dB
    spectral_error: float   # Error metric (0 = perfect, 1 = total noise)
    peak_frequency: float   # Detected dominant frequency in Hz
    signal_power: float     # Power at expected frequency
    noise_power: float      # Power outside expected frequency


# Health classification thresholds (from spec)
THRESHOLD_HEALTHY = 0.2     # spectral_error < 0.2 = healthy
THRESHOLD_SEV2 = 0.5        # 0.2 <= spectral_error < 0.5 = warning
# spectral_error >= 0.5 = critical (sev1)


def compute_fft(samples: np.ndarray, sample_rate: float) -> Tuple[np.ndarray, np.ndarray]:
    """
    Compute the FFT of the input samples.
    
    Args:
        samples: Array of time-domain samples
        sample_rate: Sampling rate in Hz
        
    Returns:
        Tuple of (frequencies, magnitudes) arrays
        - frequencies: Array of frequency bins in Hz (positive only)
        - magnitudes: Array of magnitude values for each frequency bin
    """
    n = len(samples)
    if n == 0:
        return np.array([]), np.array([])
    
    # Apply Hanning window to reduce spectral leakage
    windowed = samples * np.hanning(n)
    
    # Compute FFT
    fft_result = np.fft.rfft(windowed)
    magnitudes = np.abs(fft_result) / n
    
    # Compute frequency bins
    frequencies = np.fft.rfftfreq(n, d=1.0 / sample_rate)
    
    return frequencies, magnitudes


def find_peak_frequency(frequencies: np.ndarray, magnitudes: np.ndarray) -> float:
    """
    Find the frequency with the highest magnitude.
    
    Args:
        frequencies: Array of frequency bins in Hz
        magnitudes: Array of magnitude values
        
    Returns:
        Peak frequency in Hz
    """
    if len(magnitudes) == 0:
        return 0.0
    
    peak_idx = np.argmax(magnitudes)
    return float(frequencies[peak_idx])


def compute_snr(
    frequencies: np.ndarray,
    magnitudes: np.ndarray,
    expected_freq: float,
    bandwidth: float = 0.1
) -> Tuple[float, float, float]:
    """
    Compute Signal-to-Noise Ratio for a signal.
    
    Args:
        frequencies: Array of frequency bins in Hz
        magnitudes: Array of magnitude values
        expected_freq: The expected fundamental frequency in Hz
        bandwidth: Width around expected_freq to consider as "signal" (Hz)
        
    Returns:
        Tuple of (snr_db, signal_power, noise_power)
    """
    if len(magnitudes) == 0:
        return 0.0, 0.0, 0.0
    
    # Find bins within the signal bandwidth
    signal_mask = np.abs(frequencies - expected_freq) <= bandwidth
    
    # Compute signal and noise power
    power = magnitudes ** 2
    signal_power = np.sum(power[signal_mask])
    noise_power = np.sum(power[~signal_mask])
    
    # Avoid division by zero
    if noise_power < 1e-12:
        noise_power = 1e-12
    if signal_power < 1e-12:
        signal_power = 1e-12
    
    # SNR in decibels
    snr_db = 10 * np.log10(signal_power / noise_power)
    
    return float(snr_db), float(signal_power), float(noise_power)


def compute_spectral_error(signal_power: float, noise_power: float) -> float:
    """
    Compute spectral error metric.
    
    Error = noise / (signal + noise)
    - 0.0 = pure signal, no noise
    - 1.0 = pure noise, no signal
    
    Args:
        signal_power: Power at expected frequency
        noise_power: Power outside expected frequency
        
    Returns:
        Spectral error value between 0 and 1
    """
    total_power = signal_power + noise_power
    if total_power < 1e-12:
        return 1.0  # No signal at all = maximum error
    
    return float(noise_power / total_power)


def analyze_signal(
    samples: np.ndarray,
    sample_rate: float,
    expected_freq: float,
    bandwidth: float = 0.1
) -> SpectralMetrics:
    """
    Perform full spectral analysis on a signal.
    
    This is the main function to use for anomaly detection.
    
    Args:
        samples: Array of time-domain samples (should be WINDOW_SAMPLES long)
        sample_rate: Sampling rate in Hz (e.g., 20.0)
        expected_freq: Expected frequency for this server in Hz
        bandwidth: Width around expected_freq to consider as "signal"
        
    Returns:
        SpectralMetrics with SNR, spectral error, peak frequency, and power values
    """
    # Compute FFT
    frequencies, magnitudes = compute_fft(samples, sample_rate)
    
    # Find the actual peak frequency (for diagnostics)
    peak_freq = find_peak_frequency(frequencies, magnitudes)
    
    # Compute SNR
    snr_db, signal_power, noise_power = compute_snr(
        frequencies, magnitudes, expected_freq, bandwidth
    )
    
    # Compute spectral error
    spectral_error = compute_spectral_error(signal_power, noise_power)
    
    return SpectralMetrics(
        snr=snr_db,
        spectral_error=spectral_error,
        peak_frequency=peak_freq,
        signal_power=signal_power,
        noise_power=noise_power
    )


def classify_health(spectral_error: float) -> str:
    """
    Classify server health based on spectral error.
    
    Args:
        spectral_error: Value between 0 and 1
        
    Returns:
        "healthy", "sev2" (warning), or "sev1" (critical)
    """
    if spectral_error < THRESHOLD_HEALTHY:
        return "healthy"
    elif spectral_error < THRESHOLD_SEV2:
        return "sev2"
    else:
        return "sev1"


def compute_rack_health_score(server_spectral_errors: list[float]) -> float:
    """
    Compute overall rack health score from server spectral errors.
    
    Args:
        server_spectral_errors: List of spectral errors for each server
        
    Returns:
        Health score between 0 (all failed) and 1 (all healthy)
    """
    if not server_spectral_errors:
        return 0.0
    
    avg_error = sum(server_spectral_errors) / len(server_spectral_errors)
    return max(0.0, min(1.0, 1.0 - avg_error))
