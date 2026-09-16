"""
Section 6.7: sensitivity of ArogyaTwin's expiry/trust layer to the underlying
opportunistic relay strategy. Compares three established DTN routing
protocols (Epidemic Routing [11], binary Spray-and-Wait [12], PRoPHET [13])
run with and without ArogyaTwin's per-packet expiry check applied before
every replication/transfer decision. This is a separate, self-contained
relay-layer simulation reusing the same synthetic evidence stream as the
main experiment (Section 5), with mobile relay nodes standing in for the
device-to-device / vehicle-carried contact opportunities described in
Section 3.1.
"""
import numpy as np
from sim.core import (
    N_VILLAGES, SOURCES_PER_VILLAGE, HOURS, COMPACT_SIZE_BYTES,
    CANDIDATE_MIN_SOURCES, CANDIDATE_MIN_CONF, generate_ground_truth,
)

N_RELAYS = 6
BUFFER_CAP = 40
P_G2R = 0.15      # gateway <-> relay meeting probability per hour
P_R2H = 0.10      # relay <-> hub meeting probability per hour
P_R2R = 0.05      # relay <-> relay meeting probability per pair per hour
SPRAY_L = 8
TTL_ROUTINE, TTL_CANDIDATE = 18, 30   # representative fixed TTLs for this sub-experiment
P_INIT, BETA, GAMMA = 0.75, 0.25, 0.98


def build_packets(rng):
    fire, true_label, conf, accurate = generate_ground_truth(rng)
    packets = []
    pid = 0
    for v in range(N_VILLAGES):
        s0, s1 = v * SOURCES_PER_VILLAGE, (v + 1) * SOURCES_PER_VILLAGE
        for t in range(HOURS):
            firing_idx = [s for s in range(s0, s1) if fire[s, t]]
            if not firing_idx:
                continue
            distinct = len(firing_idx)
            c_val = float(np.mean([conf[s, t] for s in firing_idx]))
            is_candidate = distinct >= CANDIDATE_MIN_SOURCES and c_val >= CANDIDATE_MIN_CONF
            ttl = TTL_CANDIDATE if is_candidate else TTL_ROUTINE
            packets.append(dict(id=pid, village=v, created=t, ttl=ttl,
                                 true_label=any(true_label[s, t] for s in firing_idx)))
            pid += 1
    return packets


def run_protocol(rng, packets, protocol, expiry_aware):
    """Return (n_copies_transmitted, n_stale_copies, delivered_count, mean_valid_latency)."""
    delivered_time = {}
    n_copies = 0
    n_stale_copies = 0

    # custody state
    if protocol == "epidemic":
        relay_buf = [dict() for _ in range(N_RELAYS)]     # relay -> {pid: pkt}
    elif protocol == "spray":
        relay_tokens = [dict() for _ in range(N_RELAYS)]   # relay -> {pid: (pkt, tokens)}
        gw_tokens = [dict() for _ in range(N_VILLAGES)]     # village -> {pid: (pkt, tokens)}
    elif protocol == "prophet":
        relay_buf = [dict() for _ in range(N_RELAYS)]
        P_hub = np.zeros(N_RELAYS)

    by_creation = {}
    for p in packets:
        by_creation.setdefault(p["created"], []).append(p)

    for t in range(HOURS):
        # new packets injected at their gateway at their actual creation time
        if protocol == "spray":
            for p in by_creation.get(t, []):
                gw_tokens[p["village"]][p["id"]] = (p, SPRAY_L)
        # expire-and-evict pass (only when expiry_aware)
        def is_stale(p):
            return (t - p["created"]) > p["ttl"]

        if protocol in ("epidemic", "prophet") and expiry_aware:
            for buf in relay_buf:
                for pid in [k for k, v in buf.items() if is_stale(v)]:
                    del buf[pid]

        # gateway <-> relay meetings
        gw_buf = {} if protocol != "spray" else None
        if protocol in ("epidemic", "prophet"):
            gw_buf = {v: {} for v in range(N_VILLAGES)}
            for p in by_creation.get(t, []):
                gw_buf[p["village"]][p["id"]] = p

        for v in range(N_VILLAGES):
            for r in range(N_RELAYS):
                if rng.random() < P_G2R:
                    if protocol == "epidemic":
                        for pid, p in list(gw_buf[v].items()):
                            if pid not in relay_buf[r]:
                                if expiry_aware and is_stale(p):
                                    continue
                                if len(relay_buf[r]) >= BUFFER_CAP:
                                    oldest = min(relay_buf[r], key=lambda k: relay_buf[r][k]["created"])
                                    del relay_buf[r][oldest]
                                relay_buf[r][pid] = p
                                n_copies += 1
                                if is_stale(p):
                                    n_stale_copies += 1
                    elif protocol == "spray":
                        for pid, (p, tok) in list(gw_tokens[v].items()):
                            if pid in delivered_time or tok <= 1:
                                continue
                            if expiry_aware and is_stale(p):
                                del gw_tokens[v][pid]
                                continue
                            give = tok // 2
                            gw_tokens[v][pid] = (p, tok - give)
                            relay_tokens[r][pid] = (p, give)
                            n_copies += 1
                            if is_stale(p):
                                n_stale_copies += 1
                    elif protocol == "prophet":
                        for pid, p in list(gw_buf[v].items()):
                            if pid not in relay_buf[r]:
                                if expiry_aware and is_stale(p):
                                    continue
                                if len(relay_buf[r]) >= BUFFER_CAP:
                                    oldest = min(relay_buf[r], key=lambda k: relay_buf[r][k]["created"])
                                    del relay_buf[r][oldest]
                                relay_buf[r][pid] = p
                                n_copies += 1
                                if is_stale(p):
                                    n_stale_copies += 1

        # relay <-> relay meetings
        if protocol == "epidemic":
            for r1 in range(N_RELAYS):
                for r2 in range(r1 + 1, N_RELAYS):
                    if rng.random() < P_R2R:
                        for src, dst in ((r1, r2), (r2, r1)):
                            for pid, p in list(relay_buf[src].items()):
                                if pid not in relay_buf[dst]:
                                    if expiry_aware and is_stale(p):
                                        continue
                                    if len(relay_buf[dst]) >= BUFFER_CAP:
                                        oldest = min(relay_buf[dst], key=lambda k: relay_buf[dst][k]["created"])
                                        del relay_buf[dst][oldest]
                                    relay_buf[dst][pid] = p
                                    n_copies += 1
                                    if is_stale(p):
                                        n_stale_copies += 1
        elif protocol == "spray":
            for r1 in range(N_RELAYS):
                for r2 in range(r1 + 1, N_RELAYS):
                    if rng.random() < P_R2R:
                        for src, dst in ((r1, r2), (r2, r1)):
                            for pid, (p, tok) in list(relay_tokens[src].items()):
                                if pid in delivered_time or tok <= 1:
                                    continue
                                if pid in relay_tokens[dst]:
                                    continue
                                if expiry_aware and is_stale(p):
                                    del relay_tokens[src][pid]
                                    continue
                                give = tok // 2
                                if give < 1:
                                    continue
                                relay_tokens[src][pid] = (p, tok - give)
                                relay_tokens[dst][pid] = (p, give)
                                n_copies += 1
                                if is_stale(p):
                                    n_stale_copies += 1
        elif protocol == "prophet":
            for r1 in range(N_RELAYS):
                for r2 in range(r1 + 1, N_RELAYS):
                    if rng.random() < P_R2R:
                        # PRoPHET transitivity update
                        p12 = P_hub[r1] + (1 - P_hub[r1]) * P_hub[r2] * BETA
                        p21 = P_hub[r2] + (1 - P_hub[r2]) * P_hub[r1] * BETA
                        if P_hub[r2] > P_hub[r1]:
                            for pid, p in list(relay_buf[r1].items()):
                                if pid not in relay_buf[r2]:
                                    if expiry_aware and is_stale(p):
                                        continue
                                    if len(relay_buf[r2]) >= BUFFER_CAP:
                                        oldest = min(relay_buf[r2], key=lambda k: relay_buf[r2][k]["created"])
                                        del relay_buf[r2][oldest]
                                    relay_buf[r2][pid] = p
                                    n_copies += 1
                                    if is_stale(p):
                                        n_stale_copies += 1
                        if P_hub[r1] > P_hub[r2]:
                            for pid, p in list(relay_buf[r2].items()):
                                if pid not in relay_buf[r1]:
                                    if expiry_aware and is_stale(p):
                                        continue
                                    if len(relay_buf[r1]) >= BUFFER_CAP:
                                        oldest = min(relay_buf[r1], key=lambda k: relay_buf[r1][k]["created"])
                                        del relay_buf[r1][oldest]
                                    relay_buf[r1][pid] = p
                                    n_copies += 1
                                    if is_stale(p):
                                        n_stale_copies += 1
                        P_hub[r1], P_hub[r2] = p12, p21

        # relay <-> hub meetings (delivery)
        for r in range(N_RELAYS):
            if rng.random() < P_R2H:
                if protocol in ("epidemic", "prophet"):
                    for pid, p in list(relay_buf[r].items()):
                        if pid not in delivered_time and not (expiry_aware and is_stale(p)):
                            delivered_time[pid] = t
                    if protocol == "prophet":
                        P_hub[r] = P_hub[r] + (1 - P_hub[r]) * P_INIT
                elif protocol == "spray":
                    for pid, (p, tok) in list(relay_tokens[r].items()):
                        if pid not in delivered_time and not (expiry_aware and is_stale(p)):
                            delivered_time[pid] = t

        # gateway <-> hub direct meetings (rare but possible, same rate as relay)
        if protocol == "spray":
            for v in range(N_VILLAGES):
                if rng.random() < P_R2H:
                    for pid, (p, tok) in list(gw_tokens[v].items()):
                        if pid not in delivered_time and not (expiry_aware and is_stale(p)):
                            delivered_time[pid] = t

        # prophet aging
        if protocol == "prophet":
            P_hub *= GAMMA

    latencies = []
    for p in packets:
        if p["id"] in delivered_time:
            lat = delivered_time[p["id"]] - p["created"]
            if lat <= p["ttl"]:
                latencies.append(lat)

    total_bytes = n_copies * COMPACT_SIZE_BYTES
    stale_bytes = n_stale_copies * COMPACT_SIZE_BYTES
    return dict(
        n_copies=n_copies, n_stale_copies=n_stale_copies,
        stale_copy_rate=(n_stale_copies / n_copies) if n_copies else 0.0,
        total_bytes=total_bytes, stale_bytes=stale_bytes,
        n_delivered=len(delivered_time), n_generated=len(packets),
        delivery_ratio=len(delivered_time) / len(packets) if packets else 0.0,
        mean_valid_latency=float(np.mean(latencies)) if latencies else float("nan"),
    )


def run_dtn_comparison(n_trials=15, seed_offset=7000):
    protocols = ["epidemic", "spray", "prophet"]
    results = {proto: {"expiry_aware": [], "naive": []} for proto in protocols}
    for i in range(n_trials):
        seed = seed_offset + i
        rng = np.random.default_rng(seed)
        packets = build_packets(rng)
        for proto in protocols:
            for mode, aware in [("naive", False), ("expiry_aware", True)]:
                rng2 = np.random.default_rng(seed * 100 + hash(proto + mode) % 1000)
                r = run_protocol(rng2, packets, proto, aware)
                results[proto][mode].append(r)
    return results


def summarize_dtn(results):
    import numpy as np
    out = {}
    keys = ["n_copies", "stale_copy_rate", "total_bytes", "stale_bytes",
            "delivery_ratio", "mean_valid_latency"]
    for proto, modes in results.items():
        out[proto] = {}
        for mode, rows in modes.items():
            out[proto][mode] = {k: float(np.nanmean([row[k] for row in rows])) for k in keys}
    return out


if __name__ == "__main__":
    import json
    res = run_dtn_comparison()
    summary = summarize_dtn(res)
    print(json.dumps(summary, indent=2))
    with open("dtn_results.json", "w") as f:
        json.dump(summary, f, indent=2)
