from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import date

from app.llm.catalog import CATALOG
from app.llm.models import CatalogDefinition, ModelStatus


@dataclass(frozen=True)
class CatalogReport:
    provider_count: int
    model_count: int
    preview_count: int
    experimental_count: int
    free_tier_count: int
    oldest_verification: date


def build_report(catalog: CatalogDefinition) -> CatalogReport:
    models = [model for provider in catalog.providers for model in provider.models]
    return CatalogReport(
        provider_count=len(catalog.providers),
        model_count=len(models),
        preview_count=sum(model.status == ModelStatus.PREVIEW for model in models),
        experimental_count=sum(
            model.status == ModelStatus.EXPERIMENTAL for model in models
        ),
        free_tier_count=sum(model.free_tier for model in models),
        oldest_verification=min(
            provider.last_verified for provider in catalog.providers
        ),
    )


def format_report(report: CatalogReport) -> str:
    return "\n".join(
        (
            "LLM catalog is valid.",
            f"Providers: {report.provider_count}",
            f"Models: {report.model_count}",
            f"Preview: {report.preview_count}",
            f"Experimental: {report.experimental_count}",
            f"Free tier: {report.free_tier_count}",
            f"Oldest verification: {report.oldest_verification.isoformat()}",
        )
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate and summarize ApplyKit's release-managed LLM catalog."
    )
    parser.add_argument(
        "--max-age-days",
        type=int,
        default=None,
        help="Fail when any provider verification is older than this many days.",
    )
    args = parser.parse_args()

    report = build_report(CATALOG)
    print(format_report(report))

    if args.max_age_days is not None:
        if args.max_age_days < 0:
            parser.error("--max-age-days must be zero or greater")
        age = (date.today() - report.oldest_verification).days
        if age > args.max_age_days:
            print(
                f"Catalog verification is stale: {age} days old "
                f"(maximum {args.max_age_days})."
            )
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
