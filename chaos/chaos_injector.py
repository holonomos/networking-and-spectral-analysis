#!/usr/bin/env python3
"""
Chaos Injector - Apply network chaos using tc netem via kubectl exec.

Usage:
    # Add 200ms delay + 20% packet loss to all servers in rack 0
    python chaos/chaos_injector.py --rack 0 --delay 200ms --loss 20

    # Add 50% packet loss to specific pod
    python chaos/chaos_injector.py --pod server-rack-0-3 --loss 50

    # Clear chaos from rack 0
    python chaos/chaos_injector.py --rack 0 --clear
"""

import argparse
import subprocess
import sys
from typing import List


def get_pods_in_rack(rack_id: int) -> List[str]:
    """Get all pod names in a rack."""
    cmd = [
        "kubectl", "-n", "netwatch", "get", "pods",
        "-l", f"rack={rack_id},app=server",
        "-o", "jsonpath={.items[*].metadata.name}"
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error getting pods: {result.stderr}", file=sys.stderr)
        return []
    return result.stdout.strip().split()


def apply_chaos(pod: str, delay: str = None, loss: int = None, corrupt: int = None) -> bool:
    """Apply tc netem chaos to a pod."""
    netem_args = []
    if delay:
        netem_args.append(f"delay {delay}")
    if loss:
        netem_args.append(f"loss {loss}%")
    if corrupt:
        netem_args.append(f"corrupt {corrupt}%")
    
    if not netem_args:
        print(f"No chaos parameters specified for {pod}")
        return False
    
    netem_rule = " ".join(netem_args)
    
    # First try to delete existing qdisc (ignore errors if none exists)
    clear_cmd = [
        "kubectl", "-n", "netwatch", "exec", pod, "--",
        "tc", "qdisc", "del", "dev", "eth0", "root"
    ]
    subprocess.run(clear_cmd, capture_output=True)
    
    # Apply new netem rule
    add_cmd = [
        "kubectl", "-n", "netwatch", "exec", pod, "--",
        "sh", "-c", f"tc qdisc add dev eth0 root netem {netem_rule}"
    ]
    result = subprocess.run(add_cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"❌ {pod}: Failed - {result.stderr.strip()}")
        return False
    else:
        print(f"🔥 {pod}: Applied {netem_rule}")
        return True


def clear_chaos(pod: str) -> bool:
    """Clear tc netem chaos from a pod."""
    cmd = [
        "kubectl", "-n", "netwatch", "exec", pod, "--",
        "tc", "qdisc", "del", "dev", "eth0", "root"
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"⚪ {pod}: No chaos to clear")
        return False
    else:
        print(f"✅ {pod}: Chaos cleared")
        return True


def main():
    parser = argparse.ArgumentParser(description="Apply network chaos via tc netem")
    parser.add_argument("--rack", type=int, help="Rack ID to target (0-3)")
    parser.add_argument("--pod", type=str, help="Specific pod name to target")
    parser.add_argument("--delay", type=str, help="Delay to add (e.g., 100ms, 200ms)")
    parser.add_argument("--loss", type=int, help="Packet loss percentage (0-100)")
    parser.add_argument("--corrupt", type=int, help="Packet corruption percentage (0-100)")
    parser.add_argument("--clear", action="store_true", help="Clear chaos")
    
    args = parser.parse_args()
    
    # Get target pods
    pods = []
    if args.pod:
        pods = [args.pod]
    elif args.rack is not None:
        pods = get_pods_in_rack(args.rack)
        if not pods:
            print(f"No pods found in rack {args.rack}")
            sys.exit(1)
    else:
        print("Must specify --rack or --pod")
        sys.exit(1)
    
    print(f"Targeting {len(pods)} pods: {', '.join(pods)}")
    
    # Apply or clear chaos
    for pod in pods:
        if args.clear:
            clear_chaos(pod)
        else:
            apply_chaos(pod, delay=args.delay, loss=args.loss, corrupt=args.corrupt)


if __name__ == "__main__":
    main()
