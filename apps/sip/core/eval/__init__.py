"""Research measurements for the SIP coordinator agent (#62, Studio 6).

`gate_safety` runs adversarial model outputs against the agent and counts how many the
deterministic controls block. `replay_fidelity` checks that every run replays exactly from its
audit log and that tampered logs are caught. `judge_agreement` compares the advisory quality
judge (#64) with the golden-set labels; it needs a live model and makes no call without one.
"""
