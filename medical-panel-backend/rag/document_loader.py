"""Document loading and chunking utilities for RAG system."""

import os
import re
from pathlib import Path
from typing import List, Tuple


class DocumentLoader:
    """Load and chunk documents for embedding and retrieval."""
    
    # Chunk size in tokens (approximate: 1 token ≈ 4 characters)
    CHUNK_SIZE_TOKENS = 400
    CHUNK_OVERLAP_TOKENS = 50
    
    # Approximate conversion factor
    CHARS_PER_TOKEN = 4
    
    CHUNK_SIZE_CHARS = CHUNK_SIZE_TOKENS * CHARS_PER_TOKEN
    CHUNK_OVERLAP_CHARS = CHUNK_OVERLAP_TOKENS * CHARS_PER_TOKEN
    
    @staticmethod
    def load_text_file(file_path: str) -> str:
        """Load text content from a file.
        
        Args:
            file_path: Path to the text file
            
        Returns:
            File contents as string
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            print(f"Error loading text file {file_path}: {e}")
            return ""
    
    @staticmethod
    def load_pdf(file_path: str) -> str:
        """Load text content from a PDF file.
        
        Args:
            file_path: Path to the PDF file
            
        Returns:
            Extracted text from PDF
        """
        try:
            import pypdf
            text = ""
            with open(file_path, 'rb') as f:
                pdf_reader = pypdf.PdfReader(f)
                for page in pdf_reader.pages:
                    text += page.extract_text()
            return text
        except ImportError:
            print("pypdf not installed. Install with: pip install pypdf")
            return ""
        except Exception as e:
            print(f"Error loading PDF {file_path}: {e}")
            return ""
    
    @staticmethod
    def chunk_text(text: str, 
                   chunk_size: int = CHUNK_SIZE_CHARS,
                   overlap: int = CHUNK_OVERLAP_CHARS) -> List[str]:
        """Split text into overlapping chunks.
        
        Args:
            text: Text to chunk
            chunk_size: Size of each chunk in characters
            overlap: Overlap between chunks in characters
            
        Returns:
            List of text chunks
        """
        if len(text) <= chunk_size:
            return [text]
        
        chunks = []
        start = 0
        
        while start < len(text):
            # Find chunk end
            end = min(start + chunk_size, len(text))
            
            # Try to break at sentence boundary if not at end
            if end < len(text):
                # Look backwards for a period, newline, or sentence boundary
                last_period = text.rfind('.', start, end)
                last_newline = text.rfind('\n', start, end)
                break_point = max(last_period, last_newline)
                
                if break_point > start + chunk_size // 2:  # Only if reasonable
                    end = break_point + 1
            
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            
            # Move start position with overlap
            start = end - overlap
            if start <= 0:
                break
        
        return chunks
    
    @staticmethod
    def load_documents_from_folder(folder_path: str) -> List[Tuple[str, str, str]]:
        """Load all documents from a folder.
        
        Supports .txt and .pdf files (pdf requires pypdf).
        
        Args:
            folder_path: Path to folder containing documents
            
        Returns:
            List of tuples: (filename, content, file_path)
        """
        documents = []
        
        if not os.path.exists(folder_path):
            print(f"Documents folder not found: {folder_path}")
            return documents
        
        for file_path in Path(folder_path).rglob('*'):
            if not file_path.is_file():
                continue
            
            suffix = file_path.suffix.lower()
            
            if suffix == '.txt':
                content = DocumentLoader.load_text_file(str(file_path))
                if content.strip():
                    documents.append((file_path.name, content, str(file_path)))
            
            elif suffix == '.pdf':
                content = DocumentLoader.load_pdf(str(file_path))
                if content.strip():
                    documents.append((file_path.name, content, str(file_path)))
        
        return documents
    
    @staticmethod
    def prepare_documents(folder_path: str) -> List[Tuple[str, str, List[str]]]:
        """Load documents and chunk them.
        
        Args:
            folder_path: Path to documents folder
            
        Returns:
            List of tuples: (filename, file_path, chunks)
        """
        documents = DocumentLoader.load_documents_from_folder(folder_path)
        prepared = []
        
        for filename, content, file_path in documents:
            chunks = DocumentLoader.chunk_text(content)
            prepared.append((filename, file_path, chunks))
        
        return prepared
