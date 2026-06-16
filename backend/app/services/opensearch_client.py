"""
BomaSec — OpenSearch Client Service
=====================================
Provides query methods for the dashboard metrics endpoint.
All queries are tenant-scoped via the index pattern `alerts-{tenant_id}-*`.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from opensearchpy import OpenSearch

from app.config import get_settings

logger = logging.getLogger("bomasec.opensearch")
settings = get_settings()

# Module-level client instance
_client: Optional[OpenSearch] = None


def get_opensearch_client() -> OpenSearch:
    """Get or create the OpenSearch client singleton."""
    global _client
    if _client is None:
        _client = OpenSearch(
            hosts=[{
                "host": settings.OPENSEARCH_HOST,
                "port": settings.OPENSEARCH_PORT,
            }],
            use_ssl=False,
            verify_certs=False,
            timeout=30,
        )
        logger.info(
            "OpenSearch client initialized — %s:%s",
            settings.OPENSEARCH_HOST,
            settings.OPENSEARCH_PORT,
        )
    return _client


def _get_tenant_index_pattern(tenant_id: str) -> str:
    """Build the tenant-isolated index pattern."""
    return f"alerts-{tenant_id}-*"


async def get_dashboard_metrics(tenant_id: str) -> dict:
    """
    Query OpenSearch for dashboard metrics, strictly scoped to the tenant's indices.

    Returns severity distribution, threat timeline (24h), and top attacker IPs.
    """
    client = get_opensearch_client()
    index_pattern = _get_tenant_index_pattern(tenant_id)
    now = datetime.now(timezone.utc)
    twenty_four_hours_ago = now - timedelta(hours=24)

    # Check if any indices exist for this tenant
    try:
        index_exists = client.indices.exists(index=index_pattern)
    except Exception:
        index_exists = False

    if not index_exists:
        # No data yet — return empty metrics structure
        logger.info("No indices found for pattern '%s' — returning empty metrics", index_pattern)
        return _empty_metrics()

    try:
        # ── Combined aggregation query ──────────────────────────────────
        query = {
            "size": 0,
            "query": {
                "bool": {
                    "filter": [
                        {
                            "range": {
                                "timestamp": {
                                    "gte": twenty_four_hours_ago.isoformat(),
                                    "lte": now.isoformat(),
                                }
                            }
                        }
                    ]
                }
            },
            "aggs": {
                # Severity distribution (donut chart)
                "severity_distribution": {
                    "terms": {
                        "field": "rule.level",
                        "size": 20,
                        "order": {"_key": "desc"},
                    }
                },
                # Threat timeline (line chart — hourly buckets)
                "threat_timeline": {
                    "date_histogram": {
                        "field": "timestamp",
                        "fixed_interval": "1h",
                        "min_doc_count": 0,
                        "extended_bounds": {
                            "min": twenty_four_hours_ago.isoformat(),
                            "max": now.isoformat(),
                        },
                    }
                },
                # Top attacker IPs
                "top_attackers": {
                    "terms": {
                        "field": "data.srcip",
                        "size": 10,
                    }
                },
                # Total alerts count
                "total_count": {
                    "value_count": {
                        "field": "_id",
                    }
                },
            },
        }

        response = client.search(index=index_pattern, body=query)
        return _parse_metrics_response(response)

    except Exception as e:
        logger.error("OpenSearch query failed for tenant %s: %s", tenant_id, str(e))
        return _empty_metrics()


def _parse_metrics_response(response: dict) -> dict:
    """Parse the raw OpenSearch aggregation response into dashboard metrics."""
    aggs = response.get("aggregations", {})

    # ── Severity Distribution ───────────────────────────────────────────
    severity_colors = {
        "critical": "#ef4444",
        "high": "#f97316",
        "medium": "#eab308",
        "low": "#22c55e",
        "info": "#6366f1",
    }

    severity_buckets = aggs.get("severity_distribution", {}).get("buckets", [])
    severity_distribution = []
    for bucket in severity_buckets:
        level = _classify_severity(bucket["key"])
        severity_distribution.append({
            "level": level,
            "count": bucket["doc_count"],
            "color": severity_colors.get(level, "#71717a"),
        })

    # ── Threat Timeline ─────────────────────────────────────────────────
    timeline_buckets = aggs.get("threat_timeline", {}).get("buckets", [])
    threat_timeline = [
        {
            "timestamp": bucket["key_as_string"],
            "count": bucket["doc_count"],
        }
        for bucket in timeline_buckets
    ]

    # ── Top Attackers ───────────────────────────────────────────────────
    attacker_buckets = aggs.get("top_attackers", {}).get("buckets", [])
    top_attackers = [
        {
            "ip": bucket["key"],
            "count": bucket["doc_count"],
            "country": None,  # GeoIP enrichment in future phase
        }
        for bucket in attacker_buckets
    ]

    total_alerts = int(aggs.get("total_count", {}).get("value", 0))

    return {
        "severity_distribution": severity_distribution,
        "threat_timeline": threat_timeline,
        "top_attackers": top_attackers,
        "total_alerts": total_alerts,
        "time_range": "24h",
    }


def _classify_severity(level: int) -> str:
    """Map Wazuh numeric rule levels to severity labels."""
    if level >= 12:
        return "critical"
    elif level >= 8:
        return "high"
    elif level >= 4:
        return "medium"
    elif level >= 2:
        return "low"
    else:
        return "info"


def _empty_metrics() -> dict:
    """Return an empty metrics structure when no data is available."""
    return {
        "severity_distribution": [
            {"level": "critical", "count": 0, "color": "#ef4444"},
            {"level": "high", "count": 0, "color": "#f97316"},
            {"level": "medium", "count": 0, "color": "#eab308"},
        ],
        "threat_timeline": [],
        "top_attackers": [],
        "total_alerts": 0,
        "time_range": "24h",
    }
