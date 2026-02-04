from __future__ import annotations

from argparse import ArgumentParser
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete

from db.models import LLMMediatorBudgetDaily, LLMMediatorRouteMetric
from db.session import SessionLocal


def parse_args() -> ArgumentParser:
    parser = ArgumentParser(description="Prune LLM mediator persistence tables")
    parser.add_argument("--metrics-days", type=int, default=30)
    parser.add_argument("--budget-days", type=int, default=120)
    return parser


def main() -> int:
    args = parse_args().parse_args()
    today = datetime.now(timezone.utc).date()
    metrics_cutoff = today - timedelta(days=max(0, args.metrics_days))
    budget_cutoff = today - timedelta(days=max(0, args.budget_days))
    with SessionLocal() as session:
        metrics_deleted = session.execute(
            delete(LLMMediatorRouteMetric).where(LLMMediatorRouteMetric.day < metrics_cutoff)
        ).rowcount
        budget_deleted = session.execute(
            delete(LLMMediatorBudgetDaily).where(LLMMediatorBudgetDaily.day < budget_cutoff)
        ).rowcount
        session.commit()
    print(
        f"[llm-mediator-retention] metrics_deleted={metrics_deleted or 0} "
        f"budget_deleted={budget_deleted or 0} "
        f"metrics_cutoff={metrics_cutoff.isoformat()} budget_cutoff={budget_cutoff.isoformat()}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
