"""
SEC filings processing utilities.
Handles SEC filing download, metadata, listing items, and section content extraction.
"""

from typing import List, Optional, Any
import argparse
import sys
from config import SEC_EDGAR_IDENTITY
from utils.display_data import display_table
from edgar import Company, set_identity


def get_company_filing(
    ticker: str,
    form_type: str = "10-K",
    count: int = 1,
    year: Optional[int] = None,
    amendments: bool = False,
) -> Optional[Any]:
    """
    Get a filing for a company. If year is provided, returns the filing for that year if available,
    otherwise returns the latest.

    Args:
        ticker: Stock ticker symbol
        form_type: Type of SEC form (default: "10-K")
        count: Number of latest filings to retrieve (used when year is not specified)
        year: Specific filing year to fetch
        amendments: Whether to include amendments

    Returns:
        Filing object or None if not found
    """
    try:
        # Set SEC EDGAR identity for API compliance if supported by library
        set_identity(SEC_EDGAR_IDENTITY)

        company = Company(ticker)

        if year is not None:
            filings = (
                company.get_filings(form=form_type, year=year)
                .filter(amendments=amendments)
                .latest(count)
            )
        else:
            filings = (
                company.get_filings(form=form_type)
                .filter(amendments=amendments)
                .latest(count)
            )

        return filings

    except Exception as e:
        print(f"Error fetching filing for {ticker}: {e}")
        return None


def extract_filing_metadata(filing: Any) -> dict:
    """
    Extract metadata from a SEC filing object.

    Args:
        filing: SEC filing object

    Returns:
        Dictionary containing filing metadata
    """
    try:
        # Use EntityFiling properties only (no legacy fallbacks)
        metadata = {
            "cik": getattr(filing, "cik", None),
            "company": getattr(filing, "company", None),
            "form": getattr(filing, "form", None),
            "filing_date": getattr(filing, "filing_date", None),
            "report_date": getattr(filing, "report_date", None),
            "acceptance_datetime": getattr(filing, "acceptance_datetime", None),
            "accession_no": getattr(filing, "accession_no", None),
            "file_number": getattr(filing, "file_number", None),
            "items": getattr(filing, "items", []),
            "size": getattr(filing, "size", None),
            "primary_document": getattr(filing, "primary_document", None),
            "primary_doc_description": getattr(filing, "primary_doc_description", None),
            "is_xbrl": getattr(filing, "is_xbrl", None),
            "is_inline_xbrl": getattr(filing, "is_inline_xbrl", None),
        }

        return metadata
    except Exception as e:
        print(f"Error extracting filing metadata: {e}")
        return {}


def validate_filing_data(filing: Any) -> bool:
    """
    Validate that a filing object has the required data.

    Args:
        filing: SEC filing object

    Returns:
        True if filing is valid, False otherwise
    """
    try:
        if not filing:
            return False

        filing_obj = filing.obj()
        if not hasattr(filing_obj, "items") or not filing_obj.items:
            return False

        return True
    except Exception as e:
        print(f"Error validating filing data: {e}")
        return False


def get_filing_items(filing: Any) -> List[str]:
    """
    Get list of filing items from a SEC filing.

    Args:
        filing: SEC filing object

    Returns:
        List of filing item names
    """
    try:
        return filing.obj().items
    except Exception as e:
        print(f"Error getting filing items: {e}")
        return []


def get_filing_content(filing: Any, item: str) -> Optional[str]:
    """
    Get content for a specific filing item.

    Args:
        filing: SEC filing object
        item: Name of the filing item

    Returns:
        Content string or None if not found
    """
    try:
        item_content = filing.obj()[item]
        return item_content
    except Exception as e:
        print(f"Error getting filing content for item {item}: {e}")
        return None


def show_interactive_menu():
    """Show interactive menu for SEC filing processing options."""
    print("🏢 SEC Filing Processing - Interactive Menu")
    print("=" * 50)
    print()
    print("📋 Available Options:")
    print("  1. Get Company Filing")
    print("  2. Extract Filing Metadata")
    print("  3. Validate Filing Data")
    print("  4. List Filing Items")
    print("  5. Get Section Content")
    print("  6. Quick Help")
    print("  7. Exit")
    print()

    while True:
        try:
            choice = input("Enter your choice (1-8): ").strip()

            if choice == "1":
                return "get_filing"
            elif choice == "2":
                return "extract_metadata"
            elif choice == "3":
                return "validate_data"
            elif choice == "4":
                return "list_items"
            elif choice == "5":
                return "get_content"
            elif choice == "6":
                show_quick_help()
                print("\n" + "=" * 50)
                print("📋 Available Options:")
                print("  1. Get Company Filing")
                print("  2. Extract Filing Metadata")
                print("  3. Validate Filing Data")
                print("  4. List Filing Items")
                print("  5. Get Section Content")
                print("  6. Quick Help")
                print("  7. Exit")
                print()
                continue
            elif choice == "7":
                print("👋 Goodbye!")
                sys.exit(0)
            else:
                print("❌ Invalid choice. Please enter 1-7.")
                continue

        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            sys.exit(0)
        except EOFError:
            print("\n👋 Goodbye!")
            sys.exit(0)


def show_quick_help():
    """Show quick help with common options."""
    print("🏢 SEC Filing Processing - Quick Help")
    print("=" * 50)
    print()
    print("📋 AVAILABLE FUNCTIONS:")
    print("  --get-filing TICKER        Get latest filing for a company")
    print("  --extract-metadata TICKER  Extract filing metadata")
    print("  --validate-data TICKER     Validate filing data")
    print("  --list-items TICKER        List filing items")
    print("  --get-content TICKER ITEM  Get content for a specific section")
    print()
    print("⚙️  OPTIONS:")
    print("  --form-type TYPE           Form type (default: 10-K)")
    print("  --year YYYY                Filing year to retrieve (e.g., 2023)")
    print("  --count NUMBER             Number of filings to retrieve")
    print("  --limit NUMBER             Limit number of results to display")
    print("  --format FORMAT            Table format (grid, fancy_grid, simple, etc.)")
    print("  --metadata all             Display all EntityFiling fields in a table")
    print("  --quiet                    Suppress output (for scripting)")
    print()
    print("💡 QUICK EXAMPLES:")
    print("  uv run python -m utils.sec_filings_processing --get-filing AAPL")
    print(
        "  uv run python -m utils.sec_filings_processing --get-filing AAPL --year 2022"
    )
    print(
        "  uv run python -m utils.sec_filings_processing --extract-metadata GOOGL --metadata all"
    )
    print("  uv run python -m utils.sec_filings_processing  # Interactive menu")
    print()
    print("❓ For full help: --help")


def main():
    """CLI main function for SEC filing processing utilities."""
    parser = argparse.ArgumentParser(
        description="SEC Filing Processing Utilities - Download, process, and analyze SEC filings",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  uv run python -m utils.sec_filings_processing --get-filing AAPL
  uv run python -m utils.sec_filings_processing --process-content MSFT --form-type 10-Q
  uv run python -m utils.sec_filings_processing --extract-metadata GOOGL
  uv run python -m utils.sec_filings_processing  # Interactive menu
        """,
    )

    # Main function options
    parser.add_argument(
        "--get-filing", metavar="TICKER", help="Get latest filing for a company"
    )
    parser.add_argument(
        "--extract-metadata", metavar="TICKER", help="Extract filing metadata"
    )
    parser.add_argument(
        "--metadata",
        choices=["all"],
        help="Display all metadata fields when extracting",
    )
    parser.add_argument(
        "--validate-data", metavar="TICKER", help="Validate filing data"
    )
    parser.add_argument("--list-items", metavar="TICKER", help="List filing items")
    parser.add_argument(
        "--get-content",
        nargs=2,
        metavar=("TICKER", "ITEM"),
        help="Get content for specific filing item",
    )

    # Common options
    parser.add_argument("--form-type", default="10-K", help="Form type (default: 10-K)")
    parser.add_argument("--year", type=int, help="Filing year to retrieve (e.g., 2023)")
    parser.add_argument(
        "--count",
        type=int,
        default=1,
        help="Number of filings to retrieve (default: 1)",
    )
    parser.add_argument("--limit", type=int, help="Limit number of results to display")
    parser.add_argument(
        "--format",
        choices=["table", "simple", "grid", "fancy_grid", "pipe", "orgtbl", "plain"],
        default="grid",
        help="Table format for output (default: grid)",
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
        if selected_option == "get_filing":
            ticker = input("Enter ticker symbol: ").strip()
            args.get_filing = ticker
        elif selected_option == "extract_metadata":
            ticker = input("Enter ticker symbol: ").strip()
            args.extract_metadata = ticker
        elif selected_option == "validate_data":
            ticker = input("Enter ticker symbol: ").strip()
            args.validate_data = ticker
        elif selected_option == "list_items":
            ticker = input("Enter ticker symbol: ").strip()
            args.list_items = ticker
        elif selected_option == "get_content":
            ticker = input("Enter ticker symbol: ").strip()
            item = input("Enter filing item: ").strip()
            args.get_content = [ticker, item]

    try:
        # Handle get filing
        if args.get_filing:
            if not args.quiet:
                print(f"🔍 Getting {args.form_type} filing for {args.get_filing}...")

            filing = get_company_filing(
                args.get_filing, args.form_type, args.count, args.year
            )
            if filing:
                if not args.quiet:
                    print(f"✅ Successfully retrieved filing for {args.get_filing}")
                    metadata = extract_filing_metadata(filing)
                    if metadata:
                        print(f"📅 Filing Date: {metadata.get('filing_date', 'N/A')}")
                        print(f"📋 Form Type: {metadata.get('form', 'N/A')}")
                        print(
                            f"🔢 Accession Number: {metadata.get('accession_no', 'N/A')}"
                        )
            else:
                print(f"❌ Failed to retrieve filing for {args.get_filing}")

        # Handle extract metadata
        elif args.extract_metadata:
            if not args.quiet:
                print(f"📋 Extracting metadata for {args.extract_metadata}...")

            filing = get_company_filing(
                args.extract_metadata, args.form_type, args.count, args.year
            )
            if filing:
                metadata = extract_filing_metadata(filing)
                if metadata:
                    if not args.quiet:
                        print(
                            f"✅ Successfully extracted metadata for {args.extract_metadata}"
                        )
                        # Display all metadata directly from extract_filing_metadata output
                        metadata_list = [
                            {"Field": k, "Value": str(v)} for k, v in metadata.items()
                        ]
                        display_table(
                            data=metadata_list,
                            title=f"📋 Filing Metadata for {args.extract_metadata}",
                            headers=["Field", "Value"],
                            limit=args.limit,
                            table_format=args.format,
                        )
                else:
                    print(f"❌ Failed to extract metadata for {args.extract_metadata}")
            else:
                print(f"❌ Failed to retrieve filing for {args.extract_metadata}")

        # Handle validate data
        elif args.validate_data:
            if not args.quiet:
                print(f"✅ Validating filing data for {args.validate_data}...")

            filing = get_company_filing(
                args.validate_data, args.form_type, args.count, args.year
            )
            if filing:
                is_valid = validate_filing_data(filing)
                if is_valid:
                    print(f"✅ Filing data is valid for {args.validate_data}")
                else:
                    print(f"❌ Filing data is invalid for {args.validate_data}")
            else:
                print(f"❌ Failed to retrieve filing for {args.validate_data}")

        # Handle list items
        elif args.list_items:
            if not args.quiet:
                print(f"📋 Listing filing items for {args.list_items}...")

            filing = get_company_filing(
                args.list_items, args.form_type, args.count, args.year
            )
            if filing:
                items = get_filing_items(filing)
                if items:
                    if not args.quiet:
                        print(
                            f"✅ Found {len(items)} filing items for {args.list_items}"
                        )
                        # Display items in table format
                        items_list = [
                            {"Item": item, "Index": i + 1}
                            for i, item in enumerate(items)
                        ]
                        display_table(
                            data=items_list,
                            title=f"📋 Filing Items for {args.list_items}",
                            headers=["Index", "Item"],
                            limit=args.limit,
                            table_format=args.format,
                        )
                else:
                    print(f"❌ No filing items found for {args.list_items}")
            else:
                print(f"❌ Failed to retrieve filing for {args.list_items}")

        # Handle get content
        elif args.get_content:
            ticker, item = args.get_content
            if not args.quiet:
                print(f"📄 Getting content for {item} in {ticker} filing...")

            filing = get_company_filing(ticker, args.form_type, args.count, args.year)
            if filing:
                content = get_filing_content(filing, item)
                if content:
                    if not args.quiet:
                        print(
                            f"✅ Successfully retrieved content for {item} in {ticker}"
                        )
                        print(f"📊 Content length: {len(content)} characters")
                        if args.limit:
                            # Show first N characters
                            preview = content[
                                : args.limit * 100
                            ]  # Rough character limit
                            print(f"📝 Content preview:\n{preview}...")
                        else:
                            print(f"📝 Content:\n{content}")
                else:
                    print(f"❌ Failed to retrieve content for {item} in {ticker}")
            else:
                print(f"❌ Failed to retrieve filing for {ticker}")

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
