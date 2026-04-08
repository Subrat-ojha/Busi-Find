"""Process, deduplicate, and filter business data from multiple sources."""

import pandas as pd
from sources.base import Business


def merge_and_deduplicate(all_businesses: list[Business]) -> list[Business]:
    """Merge businesses from multiple sources and remove duplicates."""
    if not all_businesses:
        return []

    df = pd.DataFrame([b.to_dict() for b in all_businesses])

    df["name_normalized"] = df["name"].str.lower().str.strip()
    df["name_normalized"] = df["name_normalized"].str.replace(r"[^\w\s]", "", regex=True)

    df["info_score"] = (
        df["address"].astype(bool).astype(int)
        + df["phone"].astype(bool).astype(int)
        + df["website"].astype(bool).astype(int)
        + df["rating"].astype(bool).astype(int)
    )
    df = df.sort_values("info_score", ascending=False)
    df = df.drop_duplicates(subset=["name_normalized"], keep="first")
    df = df.drop(columns=["name_normalized", "info_score"])

    businesses = []
    for _, row in df.iterrows():
        businesses.append(Business(**row.to_dict()))

    print(f"Processor: {len(all_businesses)} total -> {len(businesses)} after dedup")
    return businesses


def filter_no_website(businesses: list[Business]) -> list[Business]:
    """Filter to only businesses WITHOUT a working website."""
    no_site = [b for b in businesses if not b.has_website]
    print(f"Filter: {len(no_site)} businesses without a website")
    return no_site


def display_results(businesses: list[Business], show_all: bool = False):
    """Display results as a simple text table."""
    if not businesses:
        print("No businesses found matching your criteria.")
        return

    label = "All Businesses" if show_all else "Businesses Without Websites"
    print(f"\n  {label} ({len(businesses)} found)")
    print("  " + "-" * 70)

    for i, biz in enumerate(businesses, 1):
        rating_str = f"{biz.rating}/5" if biz.rating else "-"
        print(f"  {i}. {biz.name}")
        if biz.address:
            print(f"     Address:  {biz.address}")
        if biz.phone:
            print(f"     Phone:    {biz.phone}")
        if biz.category:
            print(f"     Category: {biz.category}")
        print(f"     Rating:   {rating_str}")
        if biz.website:
            print(f"     Website:  {biz.website}")
        else:
            print(f"     Website:  (none)")
        print()


def export_to_csv(businesses: list[Business], filepath: str):
    """Export businesses to CSV."""
    if not businesses:
        return
    df = pd.DataFrame([b.to_dict() for b in businesses])
    df.to_csv(filepath, index=False, encoding="utf-8-sig")
    print(f"Exported {len(businesses)} businesses to: {filepath}")


def export_to_excel(businesses: list[Business], filepath: str):
    """Export businesses to Excel."""
    if not businesses:
        return
    df = pd.DataFrame([b.to_dict() for b in businesses])
    df.to_excel(filepath, index=False, engine="openpyxl")
    print(f"Exported {len(businesses)} businesses to: {filepath}")
