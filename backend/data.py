"""Synthetic seed incidents. Timestamps are relative to process start."""
from datetime import datetime, timedelta, timezone
from typing import Dict

from models import Incident, LogEntry, TimelineEvent


def _ago(minutes: int) -> datetime:
    return datetime.now(timezone.utc) - timedelta(minutes=minutes)


def _incident(id, title, description, severity, status, services, age, logs, extra_events=()):
    created = _ago(age)
    timeline = [TimelineEvent(timestamp=created, type="created", message="Incident opened by alerting")]
    for offset, type_, msg in extra_events:
        timeline.append(TimelineEvent(timestamp=created + timedelta(minutes=offset), type=type_, message=msg))
    log_entries = [
        LogEntry(timestamp=created - timedelta(minutes=len(logs) - i), level=lvl, service=svc, message=msg)
        for i, (lvl, svc, msg) in enumerate(logs)
    ]
    return Incident(
        id=id, title=title, description=description, severity=severity, status=status,
        services=services, created_at=created, logs=log_entries, timeline=timeline,
    )


def seed_incidents() -> Dict[str, Incident]:
    incidents = [
        _incident(
            "INC-1001", "Checkout API returning 5xx", "Error rate on /checkout spiked above 20%.",
            "SEV1", "open", ["checkout-api", "payments"], 12,
            [
                ("INFO", "deploy-bot", "Deploy started: checkout-api v2.14.0"),
                ("INFO", "deploy-bot", "Deploy finished: checkout-api v2.14.0"),
                ("ERROR", "checkout-api", "HTTP 500 NullPointerException in CartService.applyDiscount"),
                ("ERROR", "checkout-api", "HTTP 503 upstream payments returned 5xx"),
                ("WARN", "checkout-api", "Error rate 23% exceeds threshold 5%"),
            ],
        ),
        _incident(
            "INC-1002", "Search service pods restarting", "search-indexer pods in CrashLoopBackOff.",
            "SEV2", "acknowledged", ["search-indexer"], 45,
            [
                ("WARN", "search-indexer", "Heap usage at 92% of limit"),
                ("ERROR", "search-indexer", "java.lang.OutOfMemoryError: Java heap space"),
                ("ERROR", "kubelet", "Container search-indexer OOMKilled (exit code 137)"),
                ("INFO", "kubelet", "Back-off restarting failed container"),
            ],
            [(5, "acknowledged", "Acknowledged by on-call (alice)")],
        ),
        _incident(
            "INC-1003", "Orders DB latency high", "p99 query latency on orders-db > 2s.",
            "SEV2", "open", ["orders-service", "orders-db"], 30,
            [
                ("WARN", "orders-service", "Connection pool exhausted: 50/50 connections in use"),
                ("ERROR", "orders-service", "Timeout acquiring connection after 30000ms"),
                ("WARN", "orders-db", "Slow query: SELECT * FROM orders WHERE customer_id=? took 2400ms"),
            ],
        ),
        _incident(
            "INC-1004", "Login failures for SSO users", "Users unable to log in via SSO.",
            "SEV1", "open", ["auth-service"], 8,
            [
                ("ERROR", "auth-service", "SSL handshake failed: certificate has expired"),
                ("ERROR", "auth-service", "Failed to fetch IdP metadata: x509 certificate expired"),
            ],
        ),
        _incident(
            "INC-1005", "Notification queue backlog", "Email notifications delayed by ~20 minutes.",
            "SEV3", "acknowledged", ["notifier", "rabbitmq"], 90,
            [
                ("WARN", "rabbitmq", "Queue notifications depth 48210 exceeds 10000"),
                ("WARN", "notifier", "Consumer lag increasing, 2 of 8 workers healthy"),
                ("ERROR", "notifier", "Rate limit exceeded (429) from email provider"),
            ],
            [(10, "acknowledged", "Acknowledged by on-call (bob)")],
        ),
        _incident(
            "INC-1006", "Disk almost full on log aggregator", "logs-01 disk usage at 96%.",
            "SEV3", "open", ["log-aggregator"], 60,
            [
                ("WARN", "log-aggregator", "Disk usage /var/log at 96%"),
                ("ERROR", "log-aggregator", "No space left on device while writing segment"),
            ],
        ),
        _incident(
            "INC-1007", "Recommendations widget slow", "Homepage recommendations p95 at 1.8s.",
            "SEV4", "open", ["recs-service"], 120,
            [
                ("INFO", "recs-service", "Cache hit ratio dropped to 12%"),
                ("WARN", "recs-service", "Request took 1820ms"),
            ],
        ),
        _incident(
            "INC-1008", "Inventory sync job failed", "Nightly inventory sync did not complete.",
            "SEV3", "resolved", ["inventory-sync"], 600,
            [
                ("ERROR", "inventory-sync", "DNS resolution failed for supplier-api.example.com"),
                ("INFO", "inventory-sync", "Retry succeeded after DNS recovered"),
            ],
            [
                (15, "acknowledged", "Acknowledged by on-call (carol)"),
                (40, "resolved", "Resolved: supplier DNS recovered, job re-run"),
            ],
        ),
    ]
    return {i.id: i for i in incidents}
