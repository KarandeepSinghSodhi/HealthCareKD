"""RAG Manager: Orchestrates document storage and retrieval using Chroma."""

import os
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

try:
    import chromadb
    from chromadb.config import Settings
except (ImportError, Exception) as e:
    print(f"Warning: chromadb import error: {e}. RAG system will be disabled.")
    chromadb = None

from .document_loader import DocumentLoader


class RAGManager:
    """Manage RAG operations: load documents, embed, and retrieve context."""
    
    def __init__(self, documents_folder: str, embeddings_folder: str):
        """Initialize RAG Manager.
        
        Args:
            documents_folder: Path to folder containing source documents
            embeddings_folder: Path to folder where Chroma vector store is persisted
        """
        if chromadb is None:
            raise ImportError(
                "chromadb not installed. Install with: pip install chromadb"
            )
        
        self.documents_folder = documents_folder
        self.embeddings_folder = embeddings_folder
        
        # Create folders if they don't exist
        os.makedirs(documents_folder, exist_ok=True)
        os.makedirs(embeddings_folder, exist_ok=True)
        
        # Initialize Chroma client (persistent)
        self.client = chromadb.PersistentClient(path=embeddings_folder)
        
        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name="medical_documents",
            metadata={"hnsw:space": "cosine"}
        )
        
        self.loaded_documents: Dict[str, List[str]] = {}  # Track loaded docs
        
    def load_and_index_documents(self) -> Dict[str, Any]:
        """Load documents from folder and index them in Chroma.
        
        Returns:
            Dictionary with success status and statistics
        """
        prepared_docs = DocumentLoader.prepare_documents(self.documents_folder)
        
        if not prepared_docs:
            return {
                "status": "no_documents",
                "message": "No documents found in documents folder",
                "documents_loaded": 0,
                "chunks_loaded": 0
            }
        
        total_chunks = 0
        documents_loaded = 0
        
        for filename, file_path, chunks in prepared_docs:
            # Skip if already loaded (for incremental updates)
            if filename in self.loaded_documents:
                if self.loaded_documents[filename] == chunks:
                    continue  # No changes
            
            # Clear old embeddings for this document
            try:
                self.collection.delete(
                    where={"filename": filename}
                )
            except:
                pass  # Document not in collection yet
            
            # Add new chunks
            chunk_ids = []
            chunk_texts = []
            chunk_metadata = []
            
            for i, chunk in enumerate(chunks):
                chunk_id = f"{filename}_chunk_{i}"
                chunk_ids.append(chunk_id)
                chunk_texts.append(chunk)
                chunk_metadata.append({
                    "filename": filename,
                    "file_path": file_path,
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                    "loaded_at": datetime.now().isoformat()
                })
            
            # Add to Chroma collection
            self.collection.add(
                ids=chunk_ids,
                documents=chunk_texts,
                metadatas=chunk_metadata
            )
            
            self.loaded_documents[filename] = chunks
            documents_loaded += 1
            total_chunks += len(chunks)
        
        return {
            "status": "success",
            "message": f"Loaded {documents_loaded} documents with {total_chunks} chunks",
            "documents_loaded": documents_loaded,
            "chunks_loaded": total_chunks
        }
    
    def retrieve_context(self, query: str, top_k: int = 3) -> str:
        """Retrieve relevant context from documents using semantic search.
        
        Args:
            query: User query or context to search for
            top_k: Number of top results to retrieve
            
        Returns:
            Formatted context string with retrieved chunks
        """
        if self.collection.count() == 0:
            return ""
        
        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=min(top_k, self.collection.count())
            )
        except Exception as e:
            print(f"Error retrieving context: {e}")
            return ""
        
        if not results or not results['documents'] or not results['documents'][0]:
            return ""
        
        # Format retrieved chunks with metadata
        context_parts = []
        for i, (doc, metadata) in enumerate(zip(results['documents'][0], results['metadatas'][0])):
            filename = metadata.get('filename', 'unknown')
            chunk_idx = metadata.get('chunk_index', 0)
            
            context_parts.append(
                f"[Document: {filename}, Chunk {chunk_idx}]\n{doc}"
            )
        
        return "\n\n---\n\n".join(context_parts)
    
    def retrieve_context_with_scores(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """Retrieve relevant context with relevance scores.
        
        Args:
            query: User query or context to search for
            top_k: Number of top results to retrieve
            
        Returns:
            List of dicts with 'text', 'score', and 'metadata' keys
        """
        if self.collection.count() == 0:
            return []
        
        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=min(top_k, self.collection.count()),
                include=["documents", "metadatas", "distances"]
            )
        except Exception as e:
            print(f"Error retrieving context with scores: {e}")
            return []
        
        if not results or not results['documents'] or not results['documents'][0]:
            return []
        
        # Convert distances to relevance scores (0-1, higher is better)
        # Chroma returns cosine distances; convert to similarity
        retrieved = []
        for doc, metadata, distance in zip(
            results['documents'][0],
            results['metadatas'][0],
            results['distances'][0]
        ):
            # Cosine distance to similarity: similarity = 1 - distance
            similarity = 1 - distance
            retrieved.append({
                "text": doc,
                "score": similarity,
                "metadata": metadata
            })
        
        return retrieved
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about loaded documents and embeddings.
        
        Returns:
            Dictionary with statistics
        """
        return {
            "total_chunks": self.collection.count(),
            "documents_loaded": len(self.loaded_documents),
            "documents": list(self.loaded_documents.keys()),
            "embeddings_folder": self.embeddings_folder
        }
    
    def reload_documents(self) -> Dict[str, Any]:
        """Reload all documents from folder (clears old embeddings).
        
        Returns:
            Dictionary with success status and statistics
        """
        # Clear collection
        try:
            self.collection.delete(where={})  # Delete all
        except:
            pass
        
        self.loaded_documents.clear()
        
        # Reload
        return self.load_and_index_documents()
    
    def clear_embeddings(self) -> Dict[str, str]:
        """Clear all embeddings from Chroma collection.
        
        Returns:
            Status dictionary
        """
        try:
            self.collection.delete(where={})
            self.loaded_documents.clear()
            return {"status": "success", "message": "Embeddings cleared"}
        except Exception as e:
            return {"status": "error", "message": str(e)}
