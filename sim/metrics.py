import numpy as np
from sim.core import OUTBREAK_1, OUTBREAK_2, DEGRADED_VILLAGE, ADVERSARIAL_VILLAGE, ADVERSARIAL_WINDOW, generate_ground_truth


def compute_metrics(trial_result, seed):
    import numpy as np
    from sim.core import HOURS
    rng = np.random.default_rng(seed)
    fire, true_label, conf, accurate = generate_ground_truth(rng)  # regenerate identical ground truth (same seed)

    pkts = trial_result["packets"]
    n_delivered = len(pkts)
    n_stale = sum(1 for p in pkts if p["stale"])
    n_generated = n_delivered + trial_result["proactive_discards"]

    stale_rate = (n_stale / n_delivered) if n_delivered else 0.0
    total_bytes = sum(p["size"] for p in pkts)
    bytes_per_event = (total_bytes / n_generated) if n_generated else 0.0
    bytes_per_day = total_bytes / (HOURS / 24)

    valid_latencies = [p["latency"] for p in pkts if not p["stale"]]
    mean_valid_latency = float(np.mean(valid_latencies)) if valid_latencies else float("nan")
    median_valid_latency = float(np.median(valid_latencies)) if valid_latencies else float("nan")

    qlens = [q for (_, _, q) in trial_result["queue_trace"]]
    mean_q = float(np.mean(qlens))
    max_q = int(np.max(qlens))

    events = trial_result["verification_events"]

    def detect_latency(ob):
        onset, end = ob["onset"], ob["onset"] + ob["duration"]
        cands = [t for (t, v) in events if v == ob["village"] and onset <= t <= end + 72]
        return (min(cands) - onset) if cands else float("nan")

    lat1 = detect_latency(OUTBREAK_1)
    lat2 = detect_latency(OUTBREAK_2)

    adv_window_end = ADVERSARIAL_WINDOW[1]
    false_verifs_adv = [t for (t, v) in events if v == ADVERSARIAL_VILLAGE and t <= adv_window_end + 24]
    false_verified_adv = len(false_verifs_adv) > 0

    flagged_villages = sorted(set(v for (_, v) in events))
    true_villages = {OUTBREAK_1["village"], OUTBREAK_2["village"]}
    flagged_set = set(flagged_villages)
    tp = len(flagged_set & true_villages)
    fp = len(flagged_set - true_villages)
    fn = len(true_villages - flagged_set)
    precision = tp / (tp + fp) if (tp + fp) > 0 else float("nan")
    recall = tp / (tp + fn) if (tp + fn) > 0 else float("nan")

    ground_truth_reliability = np.array([
        accurate[v * 5:(v + 1) * 5].sum() / max(1, fire[v * 5:(v + 1) * 5].sum())
        for v in range(6)
    ])
    H_final = trial_result["H_final"]
    calib_error = float(np.mean(np.abs(H_final - ground_truth_reliability)))

    degraded_bytes = sum(p["size"] for p in pkts if p["village"] == DEGRADED_VILLAGE)
    reliable_villages = [v for v in range(6) if v not in (DEGRADED_VILLAGE, ADVERSARIAL_VILLAGE)]
    reliable_bytes = sum(p["size"] for p in pkts if p["village"] in reliable_villages)
    degraded_share = degraded_bytes / total_bytes if total_bytes else float("nan")

    return dict(
        n_generated=n_generated, n_delivered=n_delivered, n_stale=n_stale,
        stale_rate=stale_rate, total_bytes=total_bytes, bytes_per_event=bytes_per_event,
        bytes_per_day=bytes_per_day, mean_valid_latency=mean_valid_latency,
        median_valid_latency=median_valid_latency, mean_queue=mean_q, max_queue=max_q,
        detect_latency_ob1=lat1, detect_latency_ob2=lat2,
        false_verified_adversarial=false_verified_adv, n_false_verifs_adversarial=len(false_verifs_adv),
        precision=precision, recall=recall, calib_error=calib_error,
        proactive_discards=trial_result["proactive_discards"],
        degraded_bytes=degraded_bytes, reliable_bytes=reliable_bytes, degraded_share=degraded_share,
    )
