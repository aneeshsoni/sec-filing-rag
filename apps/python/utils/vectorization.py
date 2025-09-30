"""
Text vectorization utilities for SEC filing RAG system.
Handles chunking, overlapping, embedding generation, and vector storage.
"""

import argparse
import re
import numpy as np
from typing import List, Dict, Optional, Tuple, Any
from enum import Enum
import hashlib
import json
import logging
import openai
from sentence_transformers import SentenceTransformer

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ChunkingStrategy(Enum):
    """Different strategies for text chunking."""

    FIXED_SIZE = "fixed_size"
    SENTENCE = "sentence"
    PARAGRAPH = "paragraph"
    SEMANTIC = "semantic"
    SECTION = "section"


class EmbeddingModel(Enum):
    """Available embedding models."""

    OPENAI_ADA_002 = "text-embedding-ada-002"
    OPENAI_3_SMALL = "text-embedding-3-small"
    OPENAI_3_LARGE = "text-embedding-3-large"
    SENTENCE_TRANSFORMERS_ALL_MINI = "all-MiniLM-L6-v2"
    SENTENCE_TRANSFORMERS_ALL_MPNET = "all-mpnet-base-v2"


# Default configuration values
DEFAULT_CHUNK_SIZE = 1000
DEFAULT_OVERLAP_SIZE = 200
DEFAULT_MIN_CHUNK_SIZE = 100
DEFAULT_MAX_CHUNK_SIZE = 2000
DEFAULT_BATCH_SIZE = 32
DEFAULT_EMBEDDING_MODEL = EmbeddingModel.SENTENCE_TRANSFORMERS_ALL_MINI


def chunk_text(
    text: str,
    strategy: ChunkingStrategy = ChunkingStrategy.SENTENCE,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap_size: int = DEFAULT_OVERLAP_SIZE,
    min_chunk_size: int = DEFAULT_MIN_CHUNK_SIZE,
    max_chunk_size: int = DEFAULT_MAX_CHUNK_SIZE,
    metadata: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """
    Chunk text based on the specified strategy.

    Args:
        text: Input text to chunk
        strategy: Chunking strategy to use
        chunk_size: Target chunk size in characters
        overlap_size: Overlap between chunks in characters
        min_chunk_size: Minimum chunk size
        max_chunk_size: Maximum chunk size
        metadata: Optional metadata to attach to chunks

    Returns:
        List of chunk dictionaries with text, chunk_id, positions, and metadata
    """
    if metadata is None:
        metadata = {}

    if strategy == ChunkingStrategy.FIXED_SIZE:
        return _chunk_fixed_size(
            text, chunk_size, overlap_size, min_chunk_size, metadata
        )
    elif strategy == ChunkingStrategy.SENTENCE:
        return _chunk_by_sentences(
            text, chunk_size, overlap_size, min_chunk_size, max_chunk_size, metadata
        )
    elif strategy == ChunkingStrategy.PARAGRAPH:
        return _chunk_by_paragraphs(text, min_chunk_size, metadata)
    elif strategy == ChunkingStrategy.SEMANTIC:
        return _chunk_semantic(text, chunk_size, overlap_size, min_chunk_size, metadata)
    elif strategy == ChunkingStrategy.SECTION:
        return _chunk_by_sections(text, min_chunk_size, metadata)
    else:
        raise ValueError(f"Unknown chunking strategy: {strategy}")


def _chunk_fixed_size(
    text: str,
    chunk_size: int,
    overlap_size: int,
    min_chunk_size: int,
    metadata: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Chunk text into fixed-size chunks with overlap."""
    chunks = []
    start = 0
    chunk_id = 0

    while start < len(text):
        end = min(start + chunk_size, len(text))

        # Adjust end to preserve sentence boundaries
        if end < len(text):
            end = _find_sentence_boundary(text, start, end)

        chunk_text = text[start:end].strip()

        if len(chunk_text) >= min_chunk_size:
            chunk = {
                "text": chunk_text,
                "chunk_id": f"{metadata.get('source_id', 'unknown')}_{chunk_id}",
                "start_pos": start,
                "end_pos": end,
                "metadata": {
                    **metadata,
                    "chunk_index": chunk_id,
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


def _chunk_by_sentences(
    text: str,
    chunk_size: int,
    overlap_size: int,
    min_chunk_size: int,
    max_chunk_size: int,
    metadata: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Chunk text by sentences, respecting size limits."""
    sentences = _split_into_sentences(text)
    chunks = []
    current_chunk = []
    current_size = 0
    chunk_id = 0

    for sentence in sentences:
        sentence_size = len(sentence)

        # If adding this sentence would exceed max size, finalize current chunk
        if (
            current_size + sentence_size > max_chunk_size
            and current_chunk
            and current_size >= min_chunk_size
        ):
            chunk_text = " ".join(current_chunk)
            start_pos = text.find(chunk_text)
            end_pos = start_pos + len(chunk_text)

            chunk = {
                "text": chunk_text,
                "chunk_id": f"{metadata.get('source_id', 'unknown')}_{chunk_id}",
                "start_pos": start_pos,
                "end_pos": end_pos,
                "metadata": {
                    **metadata,
                    "chunk_index": chunk_id,
                    "sentence_count": len(current_chunk),
                },
            }
            chunks.append(chunk)

            # Start new chunk with overlap
            overlap_sentences = _get_overlap_sentences(current_chunk, overlap_size)
            current_chunk = overlap_sentences + [sentence]
            current_size = sum(len(s) for s in current_chunk)
            chunk_id += 1
        else:
            current_chunk.append(sentence)
            current_size += sentence_size

    # Add final chunk if it meets minimum size
    if current_chunk and current_size >= min_chunk_size:
        chunk_text = " ".join(current_chunk)
        start_pos = text.find(chunk_text)
        end_pos = start_pos + len(chunk_text)

        chunk = {
            "text": chunk_text,
            "chunk_id": f"{metadata.get('source_id', 'unknown')}_{chunk_id}",
            "start_pos": start_pos,
            "end_pos": end_pos,
            "metadata": {
                **metadata,
                "chunk_index": chunk_id,
                "sentence_count": len(current_chunk),
            },
        }
        chunks.append(chunk)

    # Update total_chunks for all chunks
    for chunk in chunks:
        chunk["metadata"]["total_chunks"] = len(chunks)

    return chunks


def _chunk_by_paragraphs(
    text: str, min_chunk_size: int, metadata: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """Chunk text by paragraphs."""
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks = []
    chunk_id = 0

    for i, paragraph in enumerate(paragraphs):
        if len(paragraph) >= min_chunk_size:
            start_pos = text.find(paragraph)
            end_pos = start_pos + len(paragraph)

            chunk = {
                "text": paragraph,
                "chunk_id": f"{metadata.get('source_id', 'unknown')}_{chunk_id}",
                "start_pos": start_pos,
                "end_pos": end_pos,
                "metadata": {
                    **metadata,
                    "chunk_index": chunk_id,
                    "paragraph_index": i,
                },
            }
            chunks.append(chunk)
            chunk_id += 1

    # Update total_chunks for all chunks
    for chunk in chunks:
        chunk["metadata"]["total_chunks"] = len(chunks)

    return chunks


def _chunk_by_sections(
    text: str, min_chunk_size: int, metadata: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """Chunk text by sections (e.g., Item 1, Item 2, etc.)."""
    # Look for common section patterns
    section_patterns = [
        r"Item\s+\d+[A-Z]?\s*[:\-]",  # Item 1:, Item 1A:, etc.
        r"Section\s+\d+[A-Z]?\s*[:\-]",  # Section 1:, etc.
        r"Part\s+[IVX]+[A-Z]?\s*[:\-]",  # Part I:, Part II:, etc.
        r"^\d+\.\s+[A-Z]",  # 1. Title, 2. Title, etc.
    ]

    sections = []
    current_section = ""
    current_title = ""

    lines = text.split("\n")
    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Check if this line starts a new section
        is_section_header = any(
            re.match(pattern, line, re.IGNORECASE) for pattern in section_patterns
        )

        if is_section_header and current_section:
            sections.append((current_title, current_section.strip()))
            current_section = line + "\n"
            current_title = line
        else:
            current_section += line + "\n"
            if not current_title and line:
                current_title = line[:50] + "..." if len(line) > 50 else line

    # Add the last section
    if current_section.strip():
        sections.append((current_title, current_section.strip()))

    chunks = []
    for i, (title, content) in enumerate(sections):
        if len(content) >= min_chunk_size:
            start_pos = text.find(content)
            end_pos = start_pos + len(content)

            chunk = {
                "text": content,
                "chunk_id": f"{metadata.get('source_id', 'unknown')}_{i}",
                "start_pos": start_pos,
                "end_pos": end_pos,
                "metadata": {
                    **metadata,
                    "chunk_index": i,
                    "section_title": title,
                    "section_type": "item" if "Item" in title else "section",
                },
            }
            chunks.append(chunk)

    # Update total_chunks for all chunks
    for chunk in chunks:
        chunk["metadata"]["total_chunks"] = len(chunks)

    return chunks


def _chunk_semantic(
    text: str,
    chunk_size: int,
    overlap_size: int,
    min_chunk_size: int,
    metadata: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Chunk text semantically (placeholder for more sophisticated semantic chunking)."""
    # For now, fall back to sentence-based chunking
    # In a more sophisticated implementation, you might use:
    # - Topic modeling
    # - Semantic similarity clustering
    # - Named entity recognition
    logger.warning(
        "Semantic chunking not fully implemented, falling back to sentence chunking"
    )
    return _chunk_by_sentences(
        text, chunk_size, overlap_size, min_chunk_size, DEFAULT_MAX_CHUNK_SIZE, metadata
    )


def _split_into_sentences(text: str) -> List[str]:
    """Split text into sentences."""
    # Simple sentence splitting - can be improved with more sophisticated NLP
    sentence_endings = r"[.!?]+"
    sentences = re.split(sentence_endings, text)
    return [s.strip() for s in sentences if s.strip()]


def _find_sentence_boundary(text: str, start: int, end: int) -> int:
    """Find the nearest sentence boundary within the given range."""
    # Look for sentence endings before the end position
    for i in range(end - 1, start, -1):
        if text[i] in ".!?":
            return i + 1
    return end


def _get_overlap_sentences(sentences: List[str], overlap_size: int) -> List[str]:
    """Get sentences for overlap based on overlap_size."""
    if not sentences:
        return []

    overlap_chars = 0
    overlap_sentences = []

    for sentence in reversed(sentences):
        if overlap_chars + len(sentence) <= overlap_size:
            overlap_sentences.insert(0, sentence)
            overlap_chars += len(sentence)
        else:
            break

    return overlap_sentences


def generate_embeddings(
    texts: List[str],
    model: EmbeddingModel = DEFAULT_EMBEDDING_MODEL,
    batch_size: int = DEFAULT_BATCH_SIZE,
    api_key: Optional[str] = None,
    normalize_embeddings: bool = True,
) -> List[np.ndarray]:
    """
    Generate embeddings for a list of texts.

    Args:
        texts: List of text strings
        model: Embedding model to use
        batch_size: Batch size for processing
        api_key: API key for OpenAI models
        normalize_embeddings: Whether to normalize embeddings

    Returns:
        List of embedding vectors
    """
    if not texts:
        return []

    if model.value.startswith("text-embedding"):
        return _generate_openai_embeddings(texts, model, batch_size, api_key)
    else:
        return _generate_sentence_transformer_embeddings(
            texts, model, batch_size, normalize_embeddings
        )


def _generate_openai_embeddings(
    texts: List[str], model: EmbeddingModel, batch_size: int, api_key: Optional[str]
) -> List[np.ndarray]:
    """Generate embeddings using OpenAI API."""
    if openai is None:
        raise ImportError(
            "OpenAI library not available. Install with: pip install openai"
        )

    if not api_key:
        raise ValueError("OpenAI API key required for OpenAI models")

    openai.api_key = api_key
    embeddings = []

    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]

        try:
            response = openai.Embedding.create(input=batch, model=model.value)

            batch_embeddings = [
                np.array(item["embedding"]) for item in response["data"]
            ]
            embeddings.extend(batch_embeddings)

        except Exception as e:
            logger.error(f"Error generating OpenAI embeddings for batch {i}: {e}")
            # Add zero vectors as fallback
            embeddings.extend([np.zeros(1536) for _ in batch])

    return embeddings


def _generate_sentence_transformer_embeddings(
    texts: List[str], model: EmbeddingModel, batch_size: int, normalize_embeddings: bool
) -> List[np.ndarray]:
    """Generate embeddings using Sentence Transformers."""
    if SentenceTransformer is None:
        raise ImportError(
            "Sentence Transformers not available. Install with: pip install sentence-transformers"
        )

    sentence_model = SentenceTransformer(model.value)
    embeddings = sentence_model.encode(
        texts,
        batch_size=batch_size,
        normalize_embeddings=normalize_embeddings,
        show_progress_bar=True,
    )

    return [np.array(embedding) for embedding in embeddings]


def generate_single_embedding(
    text: str,
    model: EmbeddingModel = DEFAULT_EMBEDDING_MODEL,
    api_key: Optional[str] = None,
) -> np.ndarray:
    """Generate embedding for a single text."""
    return generate_embeddings([text], model, api_key=api_key)[0]


def save_chunks_to_file(chunks: List[Dict[str, Any]], filepath: str) -> None:
    """Save chunks to a JSON file."""
    with open(filepath, "w") as f:
        json.dump(chunks, f, indent=2, default=str)


def load_chunks_from_file(filepath: str) -> List[Dict[str, Any]]:
    """Load chunks from a JSON file."""
    with open(filepath, "r") as f:
        return json.load(f)


def search_similar_chunks(
    query: str,
    chunks: List[Dict[str, Any]],
    embeddings: np.ndarray,
    query_embedding: np.ndarray,
    top_k: int = 5,
    similarity_threshold: float = 0.0,
) -> List[Tuple[Dict[str, Any], float]]:
    """
    Search for similar chunks using cosine similarity.

    Args:
        query: Search query
        chunks: List of chunk dictionaries
        embeddings: Array of chunk embeddings
        query_embedding: Query embedding vector
        top_k: Number of top results to return
        similarity_threshold: Minimum similarity score

    Returns:
        List of (chunk, similarity_score) tuples
    """
    if not chunks or embeddings is None:
        return []

    # Calculate cosine similarities
    similarities = np.dot(embeddings, query_embedding) / (
        np.linalg.norm(embeddings, axis=1) * np.linalg.norm(query_embedding)
    )

    # Get top-k results above threshold
    top_indices = np.argsort(similarities)[::-1]
    results = []

    for idx in top_indices:
        if similarities[idx] >= similarity_threshold and len(results) < top_k:
            results.append((chunks[idx], float(similarities[idx])))

    return results


def process_text_pipeline(
    text: str,
    strategy: ChunkingStrategy = ChunkingStrategy.SENTENCE,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap_size: int = DEFAULT_OVERLAP_SIZE,
    min_chunk_size: int = DEFAULT_MIN_CHUNK_SIZE,
    max_chunk_size: int = DEFAULT_MAX_CHUNK_SIZE,
    embedding_model: EmbeddingModel = DEFAULT_EMBEDDING_MODEL,
    batch_size: int = DEFAULT_BATCH_SIZE,
    api_key: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Tuple[List[Dict[str, Any]], List[np.ndarray]]:
    """
    Process text through the complete vectorization pipeline.

    Args:
        text: Input text to process
        strategy: Chunking strategy
        chunk_size: Target chunk size
        overlap_size: Overlap between chunks
        min_chunk_size: Minimum chunk size
        max_chunk_size: Maximum chunk size
        embedding_model: Embedding model to use
        batch_size: Batch size for embeddings
        api_key: API key for OpenAI models
        metadata: Optional metadata

    Returns:
        Tuple of (chunks, embeddings)
    """
    if metadata is None:
        metadata = {}

    # Generate source ID if not provided
    if "source_id" not in metadata:
        metadata["source_id"] = hashlib.md5(text.encode()).hexdigest()[:8]

    # Chunk the text
    logger.info(f"Chunking text with strategy: {strategy.value}")
    chunks = chunk_text(
        text,
        strategy,
        chunk_size,
        overlap_size,
        min_chunk_size,
        max_chunk_size,
        metadata,
    )
    logger.info(f"Created {len(chunks)} chunks")

    # Generate embeddings
    texts = [chunk["text"] for chunk in chunks]
    logger.info(f"Generating embeddings for {len(texts)} chunks")
    embeddings = generate_embeddings(texts, embedding_model, batch_size, api_key)

    return chunks, embeddings


# Example usage and CLI
def main():
    parser = argparse.ArgumentParser(description="Text Vectorization Utility")
    parser.add_argument("--text", help="Text to vectorize")
    parser.add_argument("--file", help="File containing text to vectorize")
    parser.add_argument("--query", help="Search query")
    parser.add_argument(
        "--strategy",
        choices=[s.value for s in ChunkingStrategy],
        default=ChunkingStrategy.SENTENCE.value,
        help="Chunking strategy",
    )
    parser.add_argument("--chunk-size", type=int, default=1000, help="Chunk size")
    parser.add_argument("--overlap-size", type=int, default=200, help="Overlap size")
    parser.add_argument("--top-k", type=int, default=5, help="Number of search results")

    args = parser.parse_args()

    if args.text or args.file:
        # Process text
        if args.file:
            with open(args.file, "r") as f:
                text = f.read()
        else:
            text = args.text

        chunks, embeddings = process_text_pipeline(
            text,
            ChunkingStrategy(args.strategy),
            args.chunk_size,
            args.overlap_size,
            metadata={"source": "cli"},
        )
        print("Processed {} chunks".format(len(chunks)))

        for i, chunk in enumerate(chunks):
            print(f"\nChunk {i + 1}:")
            print(f"ID: {chunk['chunk_id']}")
            print(f"Text: {chunk['text'][:200]}...")
            print(f"Metadata: {chunk['metadata']}")

    if args.query:
        # Search (would need to load existing chunks/embeddings)
        print("Search functionality requires loading existing chunks and embeddings")
        print(f"Query: '{args.query}'")

    print("\nVectorization utility completed!")


if __name__ == "__main__":
    main()
