"""
Stock list utilities
Handles NYSE, NASDAQ stock data from exchanges.
"""

import requests
from typing import Optional, Dict, List
import argparse
import sys
import time
from utils.display_data import display_stock_data, display_sec_company_data


def fetch_sec_company_tickers() -> Optional[List[Dict]]:
    """
    Fetch company tickers and CIK data from SEC's company_tickers.json.

    Returns:
        List of dictionaries containing company ticker and CIK data, or None if fetch fails
    """
    url = "https://www.sec.gov/files/company_tickers.json"
    headers = {
        "User-Agent": "SEC-Filing-RAG/1.0 (contact@example.com)",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
        "Connection": "keep-alive",
    }

    try:
        # Add a delay to be respectful to SEC servers (SEC recommends 1 second)
        time.sleep(1)

        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()

        # Convert the SEC data format to a list of dictionaries
        company_list = []
        for entry in data.values():
            company_list.append(
                {
                    "cik_str": str(entry.get("cik_str", "")).zfill(
                        10
                    ),  # Pad with leading zeros
                    "ticker": entry.get("ticker", ""),
                    "title": entry.get("title", ""),
                }
            )

        print(f"✅ Successfully fetched {len(company_list)} companies from SEC")
        return company_list

    except requests.RequestException as e:
        if hasattr(e, "response") and e.response.status_code == 403:
            print("❌ SEC API access denied (403 Forbidden)")
            print(
                "💡 The SEC may be blocking requests. Try again later or check if the API endpoint has changed."
            )
        else:
            print(f"Error fetching SEC company data: {e}")
        return None
    except ValueError as e:
        print(f"Error parsing JSON from SEC: {e}")
        return None


def fetch_stock_symbols_from_nasdaq_api(exchange: str) -> Optional[List[Dict]]:
    """
    Fetch stock symbols directly from NASDAQ API.

    Args:
        exchange: Exchange name ('nyse', 'nasdaq', 'amex')

    Returns:
        List of dictionaries containing stock symbol data, or None if fetch fails
    """
    if exchange not in ["nyse", "nasdaq", "amex"]:
        print(f"Unknown exchange: {exchange}. Available: nyse, nasdaq, amex")
        return None

    url = (
        f"https://api.nasdaq.com/api/screener/stocks?exchange={exchange}&download=true"
    )
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15"
    }

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()

        # Extract the rows from the API response
        if "data" in data and "rows" in data["data"]:
            return data["data"]["rows"]
        else:
            print(f"Unexpected API response format for {exchange}")
            return None

    except requests.RequestException as e:
        print(f"Error fetching stock data from NASDAQ API for {exchange}: {e}")
        return None
    except ValueError as e:
        print(f"Error parsing JSON from NASDAQ API for {exchange}: {e}")
        return None


def fetch_stock_symbols(exchanges: Optional[List[str]] = None) -> List[Dict]:
    """
    Fetch stock symbols from specified exchanges using NASDAQ API.

    Args:
        exchanges: List of exchange names to fetch from.
                  If None, fetches from all available exchanges.
                  Valid exchanges: ['nyse', 'nasdaq', 'amex']

    Returns:
        List of dictionaries containing stock symbol data from all specified exchanges.
        Each dict includes an 'exchange' field to identify the source exchange.
    """
    if exchanges is None:
        exchanges = ["nyse", "nasdaq"]  # Default to main exchanges

    all_data = []

    for exchange in exchanges:
        print(f"🔍 Fetching {exchange.upper()} data from NASDAQ API...")
        data = fetch_stock_symbols_from_nasdaq_api(exchange)

        if data is not None:
            # Add exchange field to each record for identification
            for record in data:
                record["exchange"] = exchange
            all_data.extend(data)
            print(
                f"✅ Successfully fetched {len(data)} symbols from {exchange.upper()}"
            )
        else:
            print(f"❌ Failed to fetch data for {exchange}")

    print(f"📊 Total symbols fetched: {len(all_data)}")
    return all_data


def get_stock_data(exchanges: Optional[List[str]] = None) -> List[Dict]:
    """
    Get stock data from exchanges.

    Args:
        exchanges: List of exchange names or None for all exchanges

    Returns:
        List of dictionaries containing stock data
    """
    return fetch_stock_symbols(exchanges)


def show_interactive_menu():
    """Show interactive menu for selecting stock data options."""
    print("🚀 Stock Data Scraper - Interactive Menu")
    print("=" * 50)
    print()
    print("📈 Available Options:")
    print("  1. NYSE Stocks")
    print("  2. NASDAQ Stock")
    print("  3. All Exchanges (NYSE + NASDAQ)")
    print("  4. SEC Company Tickers & CIK Data")
    print("  5. Quick Help")
    print("  6. Exit")
    print()

    while True:
        try:
            choice = input("Enter your choice (1-6): ").strip()

            if choice == "1":
                return "nyse"
            elif choice == "2":
                return "nasdaq"
            elif choice == "3":
                return "all"
            elif choice == "4":
                return "sec"
            elif choice == "5":
                show_quick_help()
                print("\n" + "=" * 50)
                print("📈 Available Options:")
                print("  1. NYSE Stock Data")
                print("  2. NASDAQ Stock Data")
                print("  3. All Exchanges (NYSE + NASDAQ)")
                print("  4. SEC Company Tickers & CIK Data")
                print("  5. Quick Help")
                print("  6. Exit")
                print()
                continue
            elif choice == "6":
                print("👋 Goodbye!")
                sys.exit(0)
            else:
                print("❌ Invalid choice. Please enter 1-6.")
                continue

        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            sys.exit(0)
        except EOFError:
            print("\n👋 Goodbye!")
            sys.exit(0)


def show_quick_help():
    """Show quick help with common options."""
    print("🚀 Data Scrapers - Quick Help")
    print("=" * 50)
    print()
    print("📈 STOCK DATA:")
    print("  --nyse                Fetch NYSE stock data")
    print("  --nasdaq              Fetch NASDAQ stock data")
    print("  --stocks all          Fetch both NYSE and NASDAQ")
    print("  --sec                 Fetch SEC company tickers & CIK data")
    print()
    print("⚙️  OPTIONS:")
    print("  --limit [number]      Show first n results")
    print("  --format grid         Table format (grid, fancy_grid, simple, etc.)")
    print("  --save-csv            Save results to JSON file")
    print("  --quiet               Suppress output (for scripting)")
    print()
    print("💡 QUICK EXAMPLES:")
    print("  uv run python -m utils.stock_list --nyse --limit 10")
    print("  uv run python -m utils.stock_list --nasdaq --format fancy_grid")
    print("  uv run python -m utils.stock_list --stocks all --format simple")
    print("  uv run python -m utils.stock_list --sec --limit 50")
    print("  uv run python -m utils.stock_list  # Interactive menu")
    print()
    print("❓ For full help: --help")


def main():
    """CLI main function for data scrapers."""
    parser = argparse.ArgumentParser(
        description="Stock Data Scraper - Interactive and CLI interface for stock exchange data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
            Examples:
            uv run python -m utils.stock_list --nyse --limit 10
            uv run python -m utils.stock_list --stocks all --save-csv
            uv run python -m utils.stock_list --quick-help
            uv run python -m utils.stock_list  # Interactive menu
        """,
    )

    # Stock data options
    parser.add_argument(
        "--stocks",
        choices=["nyse", "nasdaq", "all"],
        help="Stock exchange data to retrieve",
    )

    # Convenience shortcuts
    parser.add_argument("--nyse", action="store_true", help="Fetch NYSE stock data")
    parser.add_argument("--nasdaq", action="store_true", help="Fetch NASDAQ stock data")
    parser.add_argument(
        "--sec", action="store_true", help="Fetch SEC company tickers & CIK data"
    )

    # Display options
    parser.add_argument(
        "--limit", type=int, help="Limit number of companies to display"
    )
    parser.add_argument(
        "--format",
        choices=["table", "simple", "grid", "fancy_grid", "pipe", "orgtbl", "plain"],
        default="grid",
        help="Table format for output (default: grid)",
    )
    parser.add_argument(
        "--save-csv", action="store_true", help="Save data to JSON file"
    )
    parser.add_argument(
        "--quiet", action="store_true", help="Suppress output (useful for scripting)"
    )
    parser.add_argument(
        "--quick-help", action="store_true", help="Show quick help with common options"
    )

    args = parser.parse_args()

    # Handle quick help
    if args.quick_help:
        show_quick_help()
        return

    # If no arguments provided, show interactive menu
    if len(sys.argv) == 1:
        selected_option = show_interactive_menu()
        # Set the appropriate argument based on user selection
        if selected_option == "nyse":
            args.nyse = True
        elif selected_option == "nasdaq":
            args.nasdaq = True
        elif selected_option == "all":
            args.stocks = "all"
        elif selected_option == "sec":
            args.sec = True

    try:
        # Handle convenience shortcuts
        if args.nyse:
            stock_data = fetch_stock_symbols(["nyse"])
            if not args.quiet:
                display_stock_data(stock_data, "nyse", args.limit, args.format)

            if args.save_csv and stock_data:
                filename = "nyse_stocks.json"
                import json

                with open(filename, "w") as f:
                    json.dump(stock_data, f, indent=2)
                if not args.quiet:
                    print(f"💾 Data saved to {filename}")

        elif args.nasdaq:
            stock_data = fetch_stock_symbols(["nasdaq"])
            if not args.quiet:
                display_stock_data(stock_data, "nasdaq", args.limit, args.format)

            if args.save_csv and stock_data:
                filename = "nasdaq_stocks.json"
                import json

                with open(filename, "w") as f:
                    json.dump(stock_data, f, indent=2)
                if not args.quiet:
                    print(f"💾 Data saved to {filename}")

        elif args.sec:
            if not args.quiet:
                print("🔍 Fetching SEC company tickers & CIK data...")
            sec_data = fetch_sec_company_tickers()
            if not args.quiet:
                display_sec_company_data(sec_data, args.limit, args.format)

            if args.save_csv and sec_data:
                filename = "sec_company_tickers.json"
                import json

                with open(filename, "w") as f:
                    json.dump(sec_data, f, indent=2)
                if not args.quiet:
                    print(f"💾 Data saved to {filename}")

        # Handle stock data requests
        elif args.stocks:
            if not args.quiet:
                print("🔍 Fetching stock data...")

            if args.stocks == "all":
                data = fetch_stock_symbols()  # None means all exchanges
                if not args.quiet:
                    display_stock_data(data, table_format=args.format)
            else:
                data = fetch_stock_symbols([args.stocks])
                if not args.quiet:
                    display_stock_data(data, args.stocks, args.limit, args.format)

            if data and args.save_csv:
                filename = f"{args.stocks}_stocks.json"
                import json

                with open(filename, "w") as f:
                    json.dump(data, f, indent=2)
                if not args.quiet:
                    print(f"💾 Data saved to {filename}")

        else:
            print("❌ Please specify a function to run")
            parser.print_help()
            sys.exit(1)

    except KeyboardInterrupt:
        print("\n👋 Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
