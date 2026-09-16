import numpy as np
from collections import deque
from sim.core import (
    N_VILLAGES, SOURCES_PER_VILLAGE, N_SOURCES, HOURS,
    TRUST_WEIGHTS, H_ALPHA, H_PRIOR, VERIFICATION_DELAY,
    TTL_MIN, TTL_MAX, K_ROUTINE, K_CANDIDATE, TTL_MAX_ROUTINE, TTL_MAX_CANDIDATE,
    B_L, B_T, LONG_TERM_WINDOW, SHORT_TERM_WINDOW,
    COMPACT_SIZE_BYTES, RAW_SIZE_BYTES, CANDIDATE_MIN_SOURCES, CANDIDATE_MIN_CONF,
    OUTBREAK_1, OUTBREAK_2, DEGRADED_VILLAGE, ADVERSARIAL_VILLAGE, ADVERSARIAL_WINDOW,
    village_of, village_drift, generate_ground_truth, contact_process, clip,
)

VERIF_THRESHOLD = 1.2
DIVERSITY_MIN_HOURS = 2
DIVERSITY_MIN_SOURCES = 3
VERIF_WINDOW = 24  # hours

CONFIGS = {
    "centralized_raw": dict(compact=False, adaptive_trust=False, dynamic_ttl=False,
                             enforce_expiry=False, diversity_check=False, label="Centralized/raw forwarding"),
    "fixed_ttl":        dict(compact=True,  adaptive_trust=True,  dynamic_ttl=False,
                             enforce_expiry=True,  diversity_check=True,  label="Fixed-TTL"),
    "fixed_trust":      dict(compact=True,  adaptive_trust=False, dynamic_ttl=True,
                             enforce_expiry=True,  diversity_check=True,  label="Fixed-trust"),
    "no_signature":     dict(compact=False, adaptive_trust=True,  dynamic_ttl=True,
                             enforce_expiry=True,  diversity_check=True,  label="(A) No compact signature"),
    "no_expiry":        dict(compact=True,  adaptive_trust=True,  dynamic_ttl=True,
                             enforce_expiry=False, diversity_check=True,  label="(D) No stale-packet discard"),
    "no_diversity":     dict(compact=True,  adaptive_trust=True,  dynamic_ttl=True,
                             enforce_expiry=True,  diversity_check=False, label="(E) No source-diversity check"),
    "full":             dict(compact=True,  adaptive_trust=True,  dynamic_ttl=True,
                             enforce_expiry=True,  diversity_check=True,  label="(F) Full ArogyaTwin"),
}
FIXED_TTL_HOURS = 24
FIXED_TRUST_VALUE = 0.70


def run_trial(scenario_name, config_name, seed, b_l=B_L, b_t=B_T, weights=None):
    from sim.core import SCENARIOS
    rng = np.random.default_rng(seed)
    cfg = CONFIGS[config_name]
    scen = SCENARIOS[scenario_name]
    w = weights or TRUST_WEIGHTS

    fire, true_label, conf, accurate = generate_ground_truth(rng)
    contact = contact_process(rng, scen)
    extra_latency = scen.get("extra_latency", 0)

    # Per-village rolling state
    H = np.full(N_VILLAGES, H_PRIOR)
    last_contact_time = np.zeros(N_VILLAGES)
    long_gaps = [deque(maxlen=LONG_TERM_WINDOW) for _ in range(N_VILLAGES)]
    short_gaps = [deque(maxlen=SHORT_TERM_WINDOW) for _ in range(N_VILLAGES)]
    queues = [[] for _ in range(N_VILLAGES)]           # list of packet dicts
    pending_feedback = [[] for _ in range(N_VILLAGES)]  # (resolve_time, true_label)

    packets_log = []          # every packet that reaches the regional hub (delivered)
    proactive_discards = 0    # packets discarded pre-transmission (expiry enforced)
    queue_len_trace = []      # (t, village, len)
    village_recent_evidence = {v: deque() for v in range(N_VILLAGES)}  # (t, distinct_src, conf, trust) window
    verification_events = []  # (t, village)

    for t in range(HOURS):
        drift_t = village_drift(t)

        # ---- 1. local ingestion & candidate packet formation ----
        for v in range(N_VILLAGES):
            s0, s1 = v * SOURCES_PER_VILLAGE, (v + 1) * SOURCES_PER_VILLAGE
            firing_idx = [s for s in range(s0, s1) if fire[s, t]]
            if firing_idx:
                distinct_sources = len(firing_idx)
                c_val = float(np.mean([conf[s, t] for s in firing_idx]))
                a_val = (distinct_sources - 1) / (SOURCES_PER_VILLAGE - 1)
                d_val = float(drift_t[v] + rng.normal(0, 0.03))
                d_val = float(clip(d_val, 0.0, 1.0))

                if cfg["adaptive_trust"]:
                    trust = w["w_H"] * H[v] + w["w_C"] * c_val + w["w_A"] * a_val - w["w_D"] * d_val
                    trust = float(clip(trust, 0.0, 1.0))
                else:
                    trust = FIXED_TRUST_VALUE

                is_candidate = (distinct_sources >= CANDIDATE_MIN_SOURCES) and (c_val >= CANDIDATE_MIN_CONF)
                evidence_class = "candidate" if is_candidate else "routine"

                # regional contact-rate estimate (long-term) & short-term latency estimate
                reg_rate = float(np.mean(long_gaps[v])) if long_gaps[v] else 6.0
                lat_est = float(np.mean(short_gaps[v])) if short_gaps[v] else reg_rate

                if cfg["dynamic_ttl"]:
                    k = K_CANDIDATE if is_candidate else K_ROUTINE
                    cap = TTL_MAX_CANDIDATE if is_candidate else TTL_MAX_ROUTINE
                    t_base = float(np.clip(k * reg_rate, TTL_MIN, cap))
                    g_t = trust
                    ttl = float(np.clip(t_base + b_l * lat_est + b_t * g_t, TTL_MIN, TTL_MAX))
                else:
                    ttl = FIXED_TTL_HOURS

                true_lab = any(true_label[s, t] for s in firing_idx)
                accurate_lab = all(accurate[s, t] for s in firing_idx)
                size = COMPACT_SIZE_BYTES if cfg["compact"] else RAW_SIZE_BYTES

                queues[v].append(dict(
                    created=t, ttl=ttl, trust=trust, size=size,
                    evidence_class=evidence_class, distinct_sources=distinct_sources,
                    conf=c_val, true_label=true_lab, accurate=accurate_lab,
                ))

        # ---- 2. per-tick queue expiry pass (proactive discard) ----
        if cfg["enforce_expiry"]:
            for v in range(N_VILLAGES):
                keep = []
                for p in queues[v]:
                    if t > p["created"] + p["ttl"]:
                        proactive_discards += 1
                    else:
                        keep.append(p)
                queues[v] = keep

        for v in range(N_VILLAGES):
            queue_len_trace.append((t, v, len(queues[v])))

        # ---- 3. contact opportunities -> transmission ----
        for v in range(N_VILLAGES):
            if contact[v, t] and queues[v]:
                gap = t - last_contact_time[v]
                if gap > 0:
                    long_gaps[v].append(gap)
                    short_gaps[v].append(gap)
                last_contact_time[v] = t
                arrival_t = t + extra_latency
                for p in queues[v]:
                    age = t - p["created"]
                    stale = age > p["ttl"]  # meaningful mainly when expiry not enforced
                    packets_log.append(dict(
                        village=v, created=p["created"], delivered=arrival_t,
                        latency=arrival_t - p["created"], size=p["size"],
                        trust=p["trust"], conf=p["conf"], true_label=p["true_label"],
                        evidence_class=p["evidence_class"], distinct_sources=p["distinct_sources"],
                        stale=stale,
                    ))
                    pending_feedback[v].append((arrival_t + VERIFICATION_DELAY, p["accurate"]))
                    if not stale:
                        village_recent_evidence[v].append(
                            (arrival_t, p["distinct_sources"], p["conf"], p["trust"])
                        )
                queues[v] = []

        # ---- 4. historical-verification feedback (EMA update of H) ----
        for v in range(N_VILLAGES):
            still_pending = []
            for (resolve_t, lab) in pending_feedback[v]:
                if resolve_t <= t:
                    outcome = 1.0 if lab else 0.0
                    H[v] = (1 - H_ALPHA) * H[v] + H_ALPHA * outcome
                else:
                    still_pending.append((resolve_t, lab))
            pending_feedback[v] = still_pending

        # ---- 5. regional verification check ----
        for v in range(N_VILLAGES):
            dq = village_recent_evidence[v]
            while dq and dq[0][0] < t - VERIF_WINDOW:
                dq.popleft()
            if not dq:
                continue
            score = sum(trust_ * conf_ for (_, _, conf_, trust_) in dq)
            distinct_hours = len(set(int(ts) for (ts, _, _, _) in dq))
            max_src = max(ds for (_, ds, _, _) in dq)
            diversity_ok = (distinct_hours >= DIVERSITY_MIN_HOURS and max_src >= DIVERSITY_MIN_SOURCES)
            if score >= VERIF_THRESHOLD and (diversity_ok or not cfg["diversity_check"]):
                verification_events.append((t, v))
                dq.clear()

    return dict(
        packets=packets_log,
        proactive_discards=proactive_discards,
        queue_trace=queue_len_trace,
        verification_events=verification_events,
        H_final=H.copy(),
    )
