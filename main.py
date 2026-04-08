"""
Busi Find - Find local businesses without websites.

Usage:
    python main.py --location "Mumbai, India" --category "restaurants"
    python main.py --location "New York, NY" --category "plumbers" --limit 30
    python main.py --location "Delhi, India" --category "salons" --export csv
    python main.py --location "London, UK" --category "bakeries" --sources google_maps,yelp
"""

import argparse
import os
import sys
from datetime import datetime

# Fix Windows encoding
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')
os.environ["PYTHONIOENCODING"] = "utf-8"

from rich.console import Console
from rich.panel import Panel

from sources import google_maps, yelp_api, foursquare_api, google_places_api
from website_checker import check_websites
from processor import (
    merge_and_deduplicate,
    filter_no_website,
    display_results,
    export_to_csv,
    export_to_excel,
)

console = Console()

AVAILABLE_SOURCES = {
    "google_maps": ("Google Maps (scraper)", google_maps.search),
    "google_api": ("Google Places API", google_places_api.search),
    "yelp": ("Yelp Fusion API", yelp_api.search),
    "foursquare": ("Foursquare API", foursquare_api.search),
}


def main():
    parser = argparse.ArgumentParser(
        description="Find local businesses that don't have a website.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py --location "Mumbai, India" --category "restaurants"
  python main.py --location "New York, NY" --category "plumbers" --limit 30 --export excel
  python main.py --location "Delhi" --category "salons" --sources google_maps,yelp
        """,
    )
    parser.add_argument(
        "--location", "-l", required=True, help="City or area to search (e.g., 'Mumbai, India')"
    )
    parser.add_argument(
        "--category", "-c", required=True, help="Business type to search (e.g., 'restaurants', 'plumbers')"
    )
    parser.add_argument(
        "--limit", "-n", type=int, default=20, help="Max results per source (default: 20)"
    )
    parser.add_argument(
        "--sources", "-s",
        default="all",
        help=f"Comma-separated sources to use: {', '.join(AVAILABLE_SOURCES.keys())}, or 'all' (default: all)",
    )
    parser.add_argument(
        "--export", "-e",
        choices=["csv", "excel", "both"],
        default="csv",
        help="Export format (default: csv)",
    )
    parser.add_argument(
        "--skip-website-check", action="store_true",
        help="Skip verifying if listed websites are actually live",
    )
    parser.add_argument(
        "--show-all", action="store_true",
        help="Show all businesses, not just those without websites",
    )

    args = parser.parse_args()

    # Header
    console.print(Panel.fit(
        "[bold cyan]Busi Find[/] - Find businesses without websites",
        subtitle="Phase 1 CLI Tool",
    ))
    console.print(f"Location: [bold]{args.location}[/]")
    console.print(f"Category: [bold]{args.category}[/]")
    console.print(f"Limit: [bold]{args.limit}[/] per source")
    console.print()

    # Determine which sources to use
    if args.sources == "all":
        sources_to_use = list(AVAILABLE_SOURCES.keys())
    else:
        sources_to_use = [s.strip() for s in args.sources.split(",")]
        for s in sources_to_use:
            if s not in AVAILABLE_SOURCES:
                console.print(f"[red]Unknown source: {s}[/]")
                console.print(f"Available: {', '.join(AVAILABLE_SOURCES.keys())}")
                return

    console.print(f"Sources: [bold]{', '.join(sources_to_use)}[/]")
    console.print()

    # Collect from all sources
    all_businesses = []
    for source_key in sources_to_use:
        source_name, search_fn = AVAILABLE_SOURCES[source_key]
        console.rule(f"[bold]{source_name}[/]")
        results = search_fn(args.location, args.category, args.limit)
        all_businesses.extend(results)
        console.print()

    if not all_businesses:
        console.print("[red]No businesses found from any source.[/]")
        console.print("Tips:")
        console.print("  - Check your API keys in .env file")
        console.print("  - Try a different location or category")
        console.print("  - Make sure Chrome is installed (for Google Maps scraper)")
        return

    # Deduplicate
    console.rule("[bold]Processing[/]")
    businesses = merge_and_deduplicate(all_businesses)

    # Check websites
    if not args.skip_website_check:
        console.rule("[bold]Verifying Websites[/]")
        businesses = check_websites(businesses)

    # Filter
    if args.show_all:
        results = businesses
    else:
        results = filter_no_website(businesses)

    # Display
    console.print()
    console.rule("[bold]Results[/]")
    display_results(results, show_all=args.show_all)

    # Export
    if results:
        console.print()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_location = args.location.replace(",", "").replace(" ", "_")
        base_name = f"businesses_{safe_location}_{args.category}_{timestamp}"
        export_dir = os.path.join(os.path.dirname(__file__), "exports")
        os.makedirs(export_dir, exist_ok=True)

        if args.export in ("csv", "both"):
            export_to_csv(results, os.path.join(export_dir, f"{base_name}.csv"))
        if args.export in ("excel", "both"):
            export_to_excel(results, os.path.join(export_dir, f"{base_name}.xlsx"))

    console.print()
    console.print("[bold green]Done![/]")


if __name__ == "__main__":
    main()
