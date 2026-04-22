# HealthCareKD - New Architecture & RAG System

## Overview

This document describes the refactored architecture with reduced LLM calls and integrated RAG (Retrieval-Augmented Generation) system.

### Key Changes

**Before (Old Architecture)**
```
POST /chat request
├─ Evaluate Whisper Protocol (N LLM calls for dropout evaluation)
└─ Generate Response (1 LLM call)
   = N+1 total LLM calls per request
```

**After (New Architecture)**
```
POST /chat request
├─ Retrieve relevant docs from Chroma (0 LLM calls - semantic search)
├─ For each specialist: Generate response with RAG context (N LLM calls)
└─ Return all specialist responses
   = N total LLM calls per request (N+1 calls eliminated!)
```

## Architecture Improvements

### 1. **Whisper Protocol Eliminated**
- **What was removed**: Specialist dropout evaluation (checked if each specialist was still relevant)
- **Impact**: Saves N LLM calls per request
- **New behavior**: All specialists in `agents_enabled.json` stay active throughout the session

### 2. **RAG System Added**
- **What it does**: Retrieves relevant medical documents and patient information before generating specialist responses
- **Technology**: Chroma vector database with semantic search
- **Storage**: Local persistent embeddings (no external API)
- **Documents**: Drop `.txt` or `.pdf` files in `/rag/documents/`

### 3. **Parallel Specialist Responses**
- **Old behavior**: Only primary specialist responded (CMO if available, else first specialist)
- **New behavior**: All specialists respond in parallel, returns dictionary of responses
- **Frontend integration**: Choose which responses to display or aggregate

---

## RAG System Setup

### Folder Structure
```
medical-panel-backend/
├── rag/
│   ├── __init__.py
│   ├── rag_manager.py           (Core RAG orchestration)
│   ├── document_loader.py        (Document loading & chunking)
│   ├── documents/                (User drops files here)
│   │   ├── sample_medical_guidelines.txt
│   │   ├── sample_patient_history.txt
│   │   └── [your documents here]
│   └── embeddings/               (Chroma persistent storage)
│       └── [vector database files]
```

### Adding Documents

1. **Prepare documents**: Create `.txt` or `.pdf` files with medical content
   - Use sample documents as templates for format
   - Supports both plain text and PDF extraction

2. **Drop in folder**: Place files in `medical-panel-backend/rag/documents/`
   ```
   rag/documents/
   ├── hospital_protocols.txt
   ├── drug_interactions.txt
   ├── clinical_guidelines.pdf
   └── patient_records.txt
   ```

3. **Reload documents**: Call the reload endpoint
   ```bash
   POST http://localhost:8000/api/reload-documents
   ```

4. **Automatic on startup**: Documents load automatically when the backend starts

### Document Format Guidelines

**For .txt files:**
```
=== SECTION TITLE ===

Detailed information about the medical topic.

Key points:
- Point 1
- Point 2
- Point 3

More detailed explanations...
```

**For .pdf files:**
- Any PDF structure supported
- Text extracted and chunked automatically
- Extracted metadata includes original chunk positions

### Document Chunking

Documents are automatically split into chunks:
- **Chunk size**: ~400 tokens (roughly 1600 characters)
- **Overlap**: ~50 tokens (roughly 200 characters)
- **Benefit**: Allows precise document retrieval and reduces token usage per request

Example:
- Medical guideline (5 pages) → 12-15 chunks
- Patient record (2 pages) → 4-5 chunks
- All chunks indexed and searchable via semantic similarity

---

## API Endpoints

### 1. GET `/api/specialists`
Returns list of all available specialists.

**Response:**
```json
[
  {
    "id": "cmo",
    "name": "Chief Medical Officer",
    "theme": "cmo",
    "colors": {...},
    "avatar": "cmo.png",
    "prompt": "You are the Chief Medical Officer..."
  },
  ...
]
```

### 2. POST `/api/chat`
Send a message and get specialist responses with RAG context.

**Request:**
```json
{
  "messages": [
    {"role": "user", "content": "Patient has chest pain"},
    {"role": "assistant", "content": "We need more information..."}
  ]
}
```

**Response:**
```json
{
  "response": "Primary specialist's response",
  "specialist_responses": {
    "cmo": "Chief Medical Officer's response...",
    "cardiologist": "Cardiologist's response...",
    "neurologist": "Neurologist's response...",
    ...
  }
}
```

**Important**: Note that `ChatRequest` no longer includes `active_specialists` - all enabled specialists in `agents_enabled.json` are always active.

### 3. POST `/api/reload-documents`
Reload all documents from the `documents/` folder into the RAG system.

**Response:**
```json
{
  "status": "success",
  "message": "Loaded 5 documents with 47 chunks",
  "documents_loaded": 5,
  "chunks_loaded": 47
}
```

### 4. GET `/api/rag-stats`
Get statistics about the RAG system.

**Response:**
```json
{
  "total_chunks": 47,
  "documents_loaded": 5,
  "documents": ["medical_guidelines.txt", "patient_history.txt", ...]
}
```

---

## How RAG Works

### 1. **Document Loading (Startup)**
```python
rag_manager = RAGManager(documents_dir, embeddings_dir)
rag_manager.load_and_index_documents()  # Indexes all docs in Chroma
```

### 2. **Query Processing (Per Request)**
```python
user_query = "Patient has chest pain"
rag_context = rag_manager.retrieve_context(user_query, top_k=3)
# Returns top 3 relevant document chunks with source metadata
```

### 3. **Context Injection (To LLM)**
```python
system_prompt = f"""
{specialist_base_prompt}

You have access to relevant medical documents:
{rag_context}

Use these documents to inform your response.
"""
response = await llm.ainvoke([SystemMessage(content=system_prompt), ...])
```

### Example RAG Flow
```
User: "Patient presents with persistent cough and fever"
    ↓
RAG Retrieval: 
  - Chunk 1: "COVID-19 symptoms include cough, fever, fatigue..."
  - Chunk 2: "Respiratory infection guidelines recommend..."
  - Chunk 3: "Patient history shows previous respiratory issues..."
    ↓
Specialist Response (with context):
  "Based on the provided medical documents, this could indicate
   a respiratory infection. Given the persistent cough and fever,
   I would recommend the diagnostic approach outlined in the
   respiratory infection guidelines..."
```

---

## LLM Call Reduction

### Comparison: Old vs New

| Metric | Old (Whisper Protocol) | New (RAG) | Saving |
|--------|----------------------|-----------|--------|
| LLM Calls per request | N+1 | N | 1 call |
| With 5 specialists | 6 calls | 5 calls | 1 call (16.7% reduction) |
| With 9 specialists | 10 calls | 9 calls | 1 call (10% reduction) |

### Additional Savings

1. **Reduced Token Usage Per Call**
   - Old: Full conversation history + specialist evaluation
   - New: Conversation + only relevant document excerpts (3-5 chunks max)

2. **Parallel Processing**
   - All specialist responses generated concurrently
   - Total time = max(individual response times), not sum

3. **No Redundant Evaluations**
   - Old: Evaluated dropout every single message
   - New: Always use same specialists for session

---

## Configuration

### `agents_enabled.json`

Controls which specialists are active:
```json
{
  "cmo": true,
  "cardiologist": true,
  "dermatologist": true,
  "allergist": true,
  "gastroenterologist": true,
  "neurologist": true,
  "orthopedist": true,
  "pediatrician": true,
  "psychiatrist": true
}
```

**Change behavior:**
- Set to `false` to disable a specialist
- All enabled specialists stay active for the entire session
- No dynamic dropout based on relevance

### `.env` File

```bash
GOOGLE_API_KEY=your_api_key_here
GOOGLE_MODEL=gemini-1.5-flash  # or another Gemini model
```

---

## Testing

### Run the Test Suite
```bash
cd medical-panel-backend
python test_rag_system.py
```

**Test Coverage:**
1. RAG system initialization
2. Document loading and indexing
3. Semantic search / context retrieval
4. AgentManager with new RAG methods
5. Single specialist response with RAG
6. All specialist responses (LLM call efficiency)

**Expected Output:**
```
✓ RAG system successfully loads and retrieves medical documents
✓ AgentManager generates specialist responses with RAG context
✓ New architecture reduces LLM calls from N+1 to N per request
✓ All specialists can respond in parallel
```

---

## Frontend Integration

### Old Request Format (DEPRECATED)
```javascript
const response = await fetch('/api/chat', {
  method: 'POST',
  body: JSON.stringify({
    messages: [...],
    active_specialists: ['cmo', 'cardiologist']  // ❌ NO LONGER USED
  })
});
```

### New Request Format
```javascript
const response = await fetch('/api/chat', {
  method: 'POST',
  body: JSON.stringify({
    messages: [
      { role: 'user', content: 'Patient query...' },
      { role: 'assistant', content: 'Previous response...' }
    ]
    // active_specialists field removed ✓
  })
});

// Response includes all specialist responses
const data = await response.json();
console.log(data.response);  // Primary specialist response
console.log(data.specialist_responses);  // All specialist responses
```

### Update Frontend Components

**Remove:**
- `active_specialists` state management
- `dropped_specialists` display logic
- Specialist filtering UI

**Add:**
- Display/toggle between specialist responses
- Consensus view (aggregate multiple perspectives)
- RAG document source citations

---

## Document Management Strategies

### Strategy 1: Hospital Protocols
```
documents/
├── admission_workflows.txt
├── medication_guidelines.txt
├── treatment_protocols.txt
└── safety_procedures.txt
```

### Strategy 2: Patient Records
```
documents/
├── patient_001_history.txt
├── patient_002_labs.txt
└── patient_records_index.txt
```

### Strategy 3: Medical Knowledge Base
```
documents/
├── cardiology_guidelines.txt
├── dermatology_conditions.txt
├── drug_interactions.txt
└── diagnostic_criteria.txt
```

### Strategy 4: Hybrid (Recommended)
Mix protocols, guidelines, and patient-specific information for comprehensive context.

---

## Troubleshooting

### Issue: RAG not retrieving relevant documents

**Solution:**
1. Check documents folder: `medical-panel-backend/rag/documents/`
2. Verify documents loaded: `GET /api/rag-stats`
3. Check query relevance - semantic search works best with medical terminology
4. Reload documents: `POST /api/reload-documents`

### Issue: LLM calls still seem high

**Cause:** Frontend might be making multiple `/chat` requests
**Solution:**
1. Check browser network tab for duplicate requests
2. Verify `generate_all_responses_with_rag()` is being called (not individual calls)
3. Confirm Whisper Protocol methods aren't still being called

### Issue: Chroma embeddings not persisting

**Cause:** Embeddings folder permissions issue
**Solution:**
```bash
# Check folder exists and is writable
ls -la medical-panel-backend/rag/embeddings/
chmod 755 medical-panel-backend/rag/embeddings/
```

### Issue: PDF files not loading

**Cause:** `pypdf` package not installed
**Solution:**
```bash
pip install pypdf
# Restart the backend server
```

---

## Performance Optimization Tips

### 1. Tune Chunk Size
- **Smaller chunks** (200 tokens): More precise retrieval, more chunks to store
- **Larger chunks** (600 tokens): Fewer chunks, more context per chunk
- Default: 400 tokens (good balance)

Adjust in `rag/document_loader.py`:
```python
CHUNK_SIZE_TOKENS = 300  # Tune this value
```

### 2. Limit Retrieved Chunks
```python
# In routes.py /chat endpoint
rag_context = rag_manager.retrieve_context(user_query, top_k=2)  # Reduce from 3 to 2
```

### 3. Use Relevance Scores
```python
chunks_with_scores = rag_manager.retrieve_context_with_scores(query, top_k=5)
# Filter: only use chunks with score > 0.7
high_relevance = [c for c in chunks_with_scores if c['score'] > 0.7]
```

### 4. Document Organization
- Keep documents focused (per specialty or per hospital unit)
- Remove irrelevant or outdated documents
- Use clear section headers for better chunking

---

## Next Steps

1. **Populate documents folder:**
   - Add hospital protocols
   - Add patient histories
   - Add clinical guidelines

2. **Test RAG retrieval:**
   ```bash
   python test_rag_system.py
   ```

3. **Start the backend:**
   ```bash
   python -m uvicorn main:app --reload
   ```

4. **Update frontend:**
   - Remove `active_specialists` from chat requests
   - Display specialist responses from `specialist_responses` object
   - Add RAG document source citations (optional)

5. **Monitor performance:**
   - Count actual LLM API calls vs expected N
   - Measure latency improvements
   - Track token usage reduction

---

## Summary

✅ **LLM Calls Reduced**: N+1 → N per request (1 call eliminated)  
✅ **RAG System**: Semantic search over medical documents  
✅ **Document Management**: Drop files in folder, auto-loads on startup  
✅ **Parallel Responses**: All specialists respond concurrently  
✅ **No Specialist Dropout**: All active specialists stay active  
✅ **Persistent Embeddings**: Fast retrieval with Chroma  
✅ **Flexible Integration**: Use documents as needed per request  

The new architecture prioritizes efficiency while maintaining comprehensive specialist perspectives!
