"""Deterministic 'AI-style' root cause suggestions based on keyword rules."""
from typing import List

from models import Incident, Suggestion

# Each rule: (cause, base confidence, keywords (any match), recommended action)
RULES = [
    ("Memory leak / insufficient memory limit", 0.6,
     ["outofmemory", "oomkilled", "heap", "exit code 137"],
     "Check recent memory growth, capture a heap dump, and consider raising the memory limit."),
    ("Database connection pool exhaustion", 0.55,
     ["connection pool", "acquiring connection", "too many connections"],
     "Look for leaked connections or slow queries holding connections; scale the pool cautiously."),
    ("Slow database queries", 0.45,
     ["slow query", "query latency", "full table scan"],
     "Review the slow query log and add missing indexes."),
    ("Faulty recent deployment", 0.5,
     ["deploy finished", "deploy started", "rollout"],
     "Compare error rates before and after the deploy; roll back if they correlate."),
    ("Expired TLS certificate", 0.7,
     ["certificate has expired", "certificate expired", "x509"],
     "Renew the certificate and add expiry monitoring."),
    ("Downstream dependency failure", 0.4,
     ["upstream", "returned 5xx", "dns resolution failed"],
     "Check the health of downstream services and enable circuit breakers."),
    ("Rate limiting by external provider", 0.5,
     ["rate limit", "429"],
     "Add backoff/retry and request a higher quota from the provider."),
    ("Disk space exhaustion", 0.65,
     ["no space left", "disk usage"],
     "Free disk space, rotate logs, and tune retention."),
    ("Consumer throughput too low for queue load", 0.4,
     ["queue", "consumer lag", "backlog"],
     "Scale consumers and investigate unhealthy workers."),
    ("Cache degradation", 0.4,
     ["cache hit ratio", "cache miss", "eviction"],
     "Check cache capacity and recent key/TTL changes."),
]

FALLBACK = Suggestion(
    cause="No known pattern matched",
    confidence=0.1,
    evidence=[],
    action="Inspect logs manually and escalate to the owning team.",
)


def suggest_root_causes(incident: Incident) -> List[Suggestion]:
    corpus = [incident.title, incident.description] + [log.message for log in incident.logs]
    suggestions = []
    for cause, base, keywords, action in RULES:
        evidence = []
        for text in corpus:
            lowered = text.lower()
            if any(k in lowered for k in keywords) and text not in evidence:
                evidence.append(text)
        if evidence:
            # More corroborating lines -> higher confidence, capped at 0.95.
            confidence = round(min(0.95, base + 0.1 * (len(evidence) - 1)), 2)
            suggestions.append(Suggestion(cause=cause, confidence=confidence, evidence=evidence, action=action))
    suggestions.sort(key=lambda s: (-s.confidence, s.cause))
    return suggestions or [FALLBACK]
