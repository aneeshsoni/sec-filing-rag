"""
SEC Filing Chunking Enhancer
Enhances your existing section-aware approach with optimal chunk sizes and metadata.
"""

from typing import Dict, List, Optional, Any
from enum import Enum


class SectionType(Enum):
    """Types of sections in SEC filings."""

    BUSINESS = "business"
    RISK_FACTORS = "risk_factors"
    FINANCIAL_STATEMENTS = "financial_statements"
    MD_A = "management_discussion"
    LEGAL = "legal"
    PROPERTIES = "properties"
    OTHER = "other"


# Optimal chunking configurations per section type
SECTION_CHUNK_CONFIGS = {
    SectionType.FINANCIAL_STATEMENTS: {
        "chunk_size": 800,
        "overlap": 100,
        "description": "Dense financial data - smaller chunks",
    },
    SectionType.RISK_FACTORS: {
        "chunk_size": 1200,
        "overlap": 250,
        "description": "Detailed risk analysis - medium chunks with more overlap",
    },
    SectionType.BUSINESS: {
        "chunk_size": 1500,
        "overlap": 300,
        "description": "Company overview - larger chunks for narrative flow",
    },
    SectionType.MD_A: {
        "chunk_size": 1400,
        "overlap": 280,
        "description": "Management analysis - analytical content",
    },
    SectionType.LEGAL: {
        "chunk_size": 1000,
        "overlap": 200,
        "description": "Legal proceedings - factual content",
    },
    SectionType.PROPERTIES: {
        "chunk_size": 900,
        "overlap": 150,
        "description": "Property information - structured data",
    },
    SectionType.OTHER: {
        "chunk_size": 1000,
        "overlap": 200,
        "description": "Other sections - default configuration",
    },
}


def get_optimal_chunk_config(section_type: SectionType) -> Dict[str, Any]:
    """
    Get optimal chunking configuration for a specific section type.

    Args:
        section_type: SectionType enum value (already classified)

    Returns:
        Dictionary with chunk_size, overlap, and description
    """
    return SECTION_CHUNK_CONFIGS[section_type]


def chunk_section_with_optimal_config(
    section_content: str,
    section_name: str,
    section_type: SectionType,
    metadata: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """
    Apply optimal chunking to a section with its already-classified type.

    Args:
        section_content: Content of the section
        section_name: Name of the section (e.g., "Item 1")
        section_type: Already-classified SectionType enum
        metadata: Optional base metadata

    Returns:
        List of chunk dictionaries
    """
    if metadata is None:
        metadata = {}

    # Get optimal configuration for this section type
    config = get_optimal_chunk_config(section_type)
    chunk_size = config["chunk_size"]
    overlap = config["overlap"]

    return sliding_window_chunk(
        section_content,
        chunk_size=chunk_size,
        overlap_size=overlap,
        metadata={
            **metadata,
            "section": section_name,
            "section_type": section_type.value,
            "chunking_strategy": f"section_aware_{section_name}",
            "optimal_chunk_size": chunk_size,
            "optimal_overlap": overlap,
        },
    )


def sliding_window_chunk(
    text: str,
    chunk_size: int = 1000,
    overlap_size: int = 200,
    metadata: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """
    Apply sliding window chunking to text.

    Args:
        text: Text to chunk
        chunk_size: Size of each chunk in characters
        overlap_size: Overlap between chunks in characters
        metadata: Optional metadata to attach to chunks

    Returns:
        List of chunk dictionaries
    """
    if metadata is None:
        metadata = {}

    chunks = []
    start = 0
    chunk_id = 0

    while start < len(text):
        end = min(start + chunk_size, len(text))

        # Adjust end to preserve sentence boundaries
        if end < len(text):
            end = _find_sentence_boundary(text, start, end)

        chunk_text = text[start:end].strip()

        if len(chunk_text) >= 100:  # Minimum chunk size
            chunk = {
                "text": chunk_text,
                "chunk_id": f"{metadata.get('source_id', 'unknown')}_{chunk_id}",
                "start_pos": start,
                "end_pos": end,
                "metadata": {
                    **metadata,
                    "chunk_index": chunk_id,
                    "chunk_size": len(chunk_text),
                    "overlap_size": overlap_size,
                    "total_chunks": None,  # Will be set later
                },
            }
            chunks.append(chunk)
            chunk_id += 1

        # Move start position with overlap
        start = end - overlap_size
        if start >= end:  # Prevent infinite loop
            start = end

    # Update total_chunks for all chunks
    for chunk in chunks:
        chunk["metadata"]["total_chunks"] = len(chunks)

    return chunks


def _find_sentence_boundary(text: str, start: int, end: int) -> int:
    """Find the nearest sentence boundary within the given range."""
    # Look for sentence endings before the end position
    for i in range(end - 1, start, -1):
        if text[i] in ".!?":
            return i + 1
    return end


def process_sec_filing_sections(
    sections_dict: Dict[str, str],
    section_types: Dict[str, SectionType],
    metadata: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """
    Process SEC filing sections with optimal chunking per section type.

    Args:
        sections_dict: Dictionary of {section_name: section_content}
        section_types: Dictionary of {section_name: SectionType} (already classified)
        metadata: Optional base metadata

    Returns:
        List of all chunks from all sections
    """
    if metadata is None:
        metadata = {}

    all_chunks = []

    for section_name, section_content in sections_dict.items():
        print(f"Processing section: {section_name}")

        # Get the already-classified section type
        section_type = section_types.get(section_name, SectionType.OTHER)

        # Get optimal config for this section type
        config = get_optimal_chunk_config(section_type)
        print(f"  Using config: {config['description']}")
        print(f"  Chunk size: {config['chunk_size']}, Overlap: {config['overlap']}")

        # Chunk this section with optimal config
        section_chunks = chunk_section_with_optimal_config(
            section_content,
            section_name,
            section_type,
            metadata={
                **metadata,
                "section_processing_timestamp": "now",  # Add timestamp
            },
        )

        print(f"  Created {len(section_chunks)} chunks")
        all_chunks.extend(section_chunks)
        print()

    print(f"Total chunks created: {len(all_chunks)}")
    return all_chunks


# Example usage
if __name__ == "__main__":
    # Example SEC filing sections
    sample_sections = {
        "Item 1": """
        ACME Technology Corporation is a leading provider of cloud computing solutions and artificial intelligence platforms.
        We design, develop, and market software products that enable businesses to leverage advanced technologies for competitive advantage.
        Our primary business focuses on three core areas: Cloud Infrastructure Services, Artificial Intelligence Solutions, and Data Analytics Platforms.
        """,
        "Item 1A": """
        Our business is subject to numerous risks and uncertainties that could materially affect our financial condition and results of operations.
        Competition in the technology sector is intense. We face competition from larger, well-established companies with greater financial resources.
        Rapid technological changes could make our products obsolete. Economic downturns could significantly impact our business.
        """,
        "Item 8": """
        CONSOLIDATED BALANCE SHEETS
        (in millions, except share data)

        Assets:
        Current Assets: $1,200
        Total Assets: $2,950

        Liabilities:
        Current Liabilities: $700
        Total Liabilities: $1,250

        Stockholders' Equity: $1,700
        """,
    }

    # Define section types (normally this would come from your parsing logic)
    section_types = {
        "Item 1": SectionType.BUSINESS,
        "Item 1A": SectionType.RISK_FACTORS,
        "Item 8": SectionType.FINANCIAL_STATEMENTS,
    }

    # Process with enhanced chunking
    chunks = process_sec_filing_sections(
        sample_sections, section_types, {"source": "example"}
    )

    print("\nChunk Examples:")
    for i, chunk in enumerate(chunks[:5]):
        print(f"\nChunk {i + 1}:")
        print(f"  Section: {chunk['metadata']['section']}")
        print(f"  Section Type: {chunk['metadata']['section_type']}")
        print(f"  Optimal Chunk Size: {chunk['metadata']['optimal_chunk_size']}")
        print(f"  Optimal Overlap: {chunk['metadata']['optimal_overlap']}")
        print(f"  Text: {chunk['text'][:100]}...")

    print("✅ Enhanced section-aware chunking completed!")
    print(f"📊 Created {len(chunks)} chunks ready for embedding")
    print("💡 Integrate with your existing embedding pipeline")
    print("\n💡 Benefits of this approach:")
    print("  - Respects document structure")
    print("  - Optimizes chunk sizes per section type")
    print("  - Maintains context within sections")
    print("  - Better for financial Q&A performance")
    print("  - Leverages your existing section parsing logic")
