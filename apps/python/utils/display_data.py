"""
Table display utilities for formatted data output.
Provides consistent table formatting across different data types.
"""

import pandas as pd
from typing import Optional, List, Dict
from tabulate import tabulate


def display_table(
    data: List[Dict],
    title: str = "Data Table",
    headers: List[str] = None,
    limit: Optional[int] = None,
    table_format: str = "grid",
    column_config: Optional[Dict[str, Dict]] = None,
) -> None:
    """
    Display data in a formatted table with consistent styling.

    Args:
        data: List of dictionaries containing the data to display
        title: Title to display above the table
        headers: List of column headers (auto-generated if None)
        limit: Maximum number of rows to display (default: 20)
        table_format: Table format for tabulate (default: "grid")
        column_config: Dictionary with column-specific configuration
                      Format: {"column_name": {"max_width": 50, "truncate": True}}
    """
    if not data:
        print(f"❌ No data available for {title}")
        return

    print(f"\n{title}")
    print("=" * 80)
    print(f"Total records: {len(data)}")

    # Prepare data for table
    display_limit = limit if limit else 20
    table_data = []

    # Auto-generate headers if not provided
    if headers is None and data:
        headers = list(data[0].keys()) if isinstance(data[0], dict) else []

    for i, record in enumerate(data[:display_limit]):
        if isinstance(record, dict):
            row = []
            for header in headers:
                value = record.get(header, "N/A")

                # Apply column-specific formatting if configured
                if column_config and header in column_config:
                    config = column_config[header]
                    max_width = config.get("max_width", None)
                    truncate = config.get("truncate", True)

                    if max_width and truncate and len(str(value)) > max_width:
                        value = str(value)[: max_width - 3] + "..."

                row.append(value)
            table_data.append([i + 1] + row)
        else:
            # Handle non-dictionary data
            table_data.append([i + 1, str(record)] + ["N/A"] * (len(headers) - 1))

    # Create table with row numbers
    table_headers = ["#"] + headers
    table = tabulate(
        table_data,
        headers=table_headers,
        tablefmt=table_format,
        stralign="left",
        numalign="left",
    )
    print(table)

    if len(data) > display_limit:
        print(f"\n... and {len(data) - display_limit} more records")


def display_stock_data(
    data: List[Dict],
    exchange: str = None,
    limit: Optional[int] = None,
    table_format: str = "grid",
) -> None:
    """Display stock data in a formatted table."""
    if not data:
        print("❌ Failed to load stock data")
        return

    title = f"📈 {exchange.upper()} Stock Symbols" if exchange else "📈 Stock Data"

    # Format and map data to consistent field names
    formatted_data = []
    for record in data:
        # Map NASDAQ API fields to our display fields
        formatted_record = {
            "symbol": record.get("symbol", "N/A"),
            "name": record.get("name", "N/A"),
            "sector": record.get("sector", "N/A"),
            "industry": record.get("industry", "N/A"),
            "ipoyear": record.get("ipoyear", "N/A"),
            "exchange": record.get("exchange", "N/A"),
        }

        # Format IPO year
        ipoyear = formatted_record["ipoyear"]
        if ipoyear != "N/A" and pd.notna(ipoyear) and str(ipoyear).strip():
            try:
                formatted_record["ipoyear"] = str(int(float(ipoyear)))
            except (ValueError, TypeError):
                formatted_record["ipoyear"] = "N/A"
        else:
            formatted_record["ipoyear"] = "N/A"

        formatted_data.append(formatted_record)

    # Define column configuration for stock data
    column_config = {
        "name": {"max_width": 30, "truncate": True},
        "sector": {"max_width": 15, "truncate": True},
        "industry": {"max_width": 20, "truncate": True},
    }

    # Define headers for stock data
    headers = ["symbol", "name", "sector", "industry", "ipoyear", "exchange"]

    display_table(
        data=formatted_data,
        title=title,
        headers=headers,
        limit=limit,
        table_format=table_format,
        column_config=column_config,
    )


def display_sec_company_data(
    data: List[Dict], limit: Optional[int] = None, table_format: str = "grid"
) -> None:
    """Display SEC company data in a formatted table."""
    if not data:
        print("❌ Failed to load SEC company data")
        return

    # Format and map data to consistent field names
    formatted_data = []
    for record in data:
        # Map SEC API fields to our display fields
        formatted_record = {
            "cik_str": record.get("cik_str", "N/A"),
            "ticker": record.get("ticker", "N/A"),
            "title": record.get("title", "N/A"),
        }
        formatted_data.append(formatted_record)

    # Define column configuration for SEC data
    column_config = {
        "title": {"max_width": 50, "truncate": True},
    }

    # Define headers for SEC data
    headers = ["cik_str", "ticker", "title"]

    display_table(
        data=formatted_data,
        title="🏢 SEC Company Tickers & CIK Data",
        headers=headers,
        limit=limit,
        table_format=table_format,
        column_config=column_config,
    )
