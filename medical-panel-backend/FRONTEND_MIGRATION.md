# Frontend Migration Guide

## Overview

The backend API has been significantly simplified. This guide shows what needs to change in your frontend code.

---

## What Changed

### ❌ Removed
- `active_specialists` field in `ChatRequest`
- `dropped_specialists` field in `ChatResponse`
- Specialist dropout/relevance evaluation logic
- Dynamic specialist filtering

### ✅ Added
- `specialist_responses` object containing all specialist responses
- RAG-augmented specialist answers
- New endpoints: `/reload-documents`, `/rag-stats`

---

## API Changes

### GET `/api/specialists`
**Response (unchanged)**
```json
[
  {
    "id": "cmo",
    "name": "Chief Medical Officer",
    "theme": "cmo",
    "colors": {...},
    "avatar": "cmo.png",
    "prompt": "..."
  },
  ...
]
```

---

### POST `/api/chat`

#### Old Request Format ❌
```javascript
{
  "messages": [
    {"role": "user", "content": "..."},
    {"role": "assistant", "content": "..."}
  ],
  "active_specialists": ["cmo", "cardiologist"]  // REMOVED
}
```

#### New Request Format ✅
```javascript
{
  "messages": [
    {"role": "user", "content": "..."},
    {"role": "assistant", "content": "..."}
  ]
  // active_specialists field removed
}
```

#### Old Response Format ❌
```json
{
  "response": "CMO response text...",
  "active_specialists": ["cmo", "cardiologist"],
  "dropped_specialists": []
}
```

#### New Response Format ✅
```json
{
  "response": "Primary specialist response (CMO if enabled, else first specialist)",
  "specialist_responses": {
    "cmo": "Chief Medical Officer's response with RAG context...",
    "cardiologist": "Cardiologist's response with RAG context...",
    "dermatologist": "Dermatologist's response...",
    "allergist": "Allergist's response...",
    "gastroenterologist": "Gastroenterologist's response...",
    "neurologist": "Neurologist's response...",
    "orthopedist": "Orthopedist's response...",
    "pediatrician": "Pediatrician's response...",
    "psychiatrist": "Psychiatrist's response..."
  }
}
```

---

### New Endpoints

#### POST `/api/reload-documents`
Reload all documents from the `documents/` folder.

**Request:**
```javascript
fetch('/api/reload-documents', {
  method: 'POST'
})
```

**Response:**
```json
{
  "status": "success",
  "message": "Loaded 5 documents with 47 chunks",
  "documents_loaded": 5,
  "chunks_loaded": 47
}
```

#### GET `/api/rag-stats`
Get RAG system statistics.

**Request:**
```javascript
fetch('/api/rag-stats')
```

**Response:**
```json
{
  "total_chunks": 47,
  "documents_loaded": 5,
  "documents": [
    "medical_guidelines.txt",
    "patient_history.txt",
    ...
  ]
}
```

---

## Component Updates

### ChatInput Component

#### Old Code ❌
```javascript
const [activeSpecialists, setActiveSpecialists] = useState([]);

async function sendMessage(userMessage) {
  const response = await fetch('/api/chat', {
    method: 'POST',
    body: JSON.stringify({
      messages: chatHistory,
      active_specialists: activeSpecialists  // ❌ REMOVE THIS
    })
  });
  
  const data = await response.json();
  setActiveSpecialists(data.active_specialists);  // ❌ Remove
  // handle dropped_specialists...  // ❌ Remove
}
```

#### New Code ✅
```javascript
async function sendMessage(userMessage) {
  const response = await fetch('/api/chat', {
    method: 'POST',
    body: JSON.stringify({
      messages: chatHistory
      // active_specialists removed ✓
    })
  });
  
  const data = await response.json();
  // All specialists always respond - no need to track active/dropped
  return data;
}
```

---

### ChatWindow Component

#### Old Code ❌
```javascript
export default function ChatWindow({ specialists }) {
  const [messages, setMessages] = useState([]);
  const [activeSpecialists, setActiveSpecialists] = useState([]);
  const [droppedSpecialists, setDroppedSpecialists] = useState([]);

  async function handleSendMessage(text) {
    const response = await fetch('/api/chat', {
      method: 'POST',
      body: JSON.stringify({
        messages: messages,
        active_specialists: activeSpecialists  // ❌ Remove
      })
    });

    const data = await response.json();
    setMessages([...messages, 
      {role: 'user', content: text},
      {role: 'assistant', content: data.response}
    ]);
    
    // ❌ Remove this logic
    setActiveSpecialists(data.active_specialists);
    setDroppedSpecialists(data.dropped_specialists);
    
    if (data.dropped_specialists.length > 0) {
      // Show notification of dropped specialists
    }
  }

  return (
    <div>
      <MessageList messages={messages} />
      <ChatInput onSendMessage={handleSendMessage} />
      {droppedSpecialists.length > 0 && (
        <Alert>Dropped: {droppedSpecialists.join(', ')}</Alert>
      )}
    </div>
  );
}
```

#### New Code ✅
```javascript
export default function ChatWindow({ specialists }) {
  const [messages, setMessages] = useState([]);
  const [specialistResponses, setSpecialistResponses] = useState({});

  async function handleSendMessage(text) {
    const response = await fetch('/api/chat', {
      method: 'POST',
      body: JSON.stringify({
        messages: messages
        // active_specialists removed ✓
      })
    });

    const data = await response.json();
    setMessages([...messages, 
      {role: 'user', content: text},
      {role: 'assistant', content: data.response}
    ]);
    
    // Store all specialist responses
    setSpecialistResponses(data.specialist_responses || {});
  }

  return (
    <div>
      <MessageList messages={messages} />
      {specialistResponses && (
        <SpecialistPanel responses={specialistResponses} />
      )}
      <ChatInput onSendMessage={handleSendMessage} />
    </div>
  );
}
```

---

### SpecialistPanel Component

#### Old Code ❌
```javascript
export default function SpecialistPanel({ activeSpecialists, specialists }) {
  return (
    <div className="specialist-panel">
      <h3>Active Specialists ({activeSpecialists.length})</h3>
      <div className="specialist-list">
        {activeSpecialists.map(id => {
          const spec = specialists.find(s => s.id === id);
          return (
            <div key={id} className="specialist-badge">
              {spec.name}
            </div>
          );
        })}
      </div>
    </div>
  );
}
```

#### New Code ✅ (Option 1: Tabbed View)
```javascript
export default function SpecialistPanel({ responses }) {
  const [selectedSpecialist, setSelectedSpecialist] = useState(
    Object.keys(responses)[0]
  );

  return (
    <div className="specialist-panel">
      <div className="specialist-tabs">
        {Object.keys(responses).map(id => (
          <button
            key={id}
            className={selectedSpecialist === id ? 'active' : ''}
            onClick={() => setSelectedSpecialist(id)}
          >
            {id}
          </button>
        ))}
      </div>
      <div className="specialist-response">
        <h4>{selectedSpecialist}</h4>
        <p>{responses[selectedSpecialist]}</p>
      </div>
    </div>
  );
}
```

#### New Code ✅ (Option 2: Stack View)
```javascript
export default function SpecialistPanel({ responses }) {
  return (
    <div className="specialist-panel">
      <h3>Specialist Opinions</h3>
      <div className="specialist-stack">
        {Object.entries(responses).map(([id, response]) => (
          <div key={id} className="specialist-card">
            <h4>{id === 'cmo' ? 'Chief Medical Officer' : id}</h4>
            <p>{response}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
```

#### New Code ✅ (Option 3: Consensus View)
```javascript
export default function SpecialistPanel({ responses, primaryResponse }) {
  const [showAllResponses, setShowAllResponses] = useState(false);

  return (
    <div className="specialist-panel">
      <div className="primary-response">
        <h4>Primary Assessment</h4>
        <p>{primaryResponse}</p>
      </div>
      
      {showAllResponses && (
        <div className="all-responses">
          <h4>Other Specialist Perspectives</h4>
          {Object.entries(responses).map(([id, response]) => (
            <details key={id}>
              <summary>{id}</summary>
              <p>{response}</p>
            </details>
          ))}
        </div>
      )}
      
      <button onClick={() => setShowAllResponses(!showAllResponses)}>
        {showAllResponses ? 'Hide' : 'Show'} All Specialist Opinions
      </button>
    </div>
  );
}
```

---

### App.jsx/Context Updates

#### Old Code ❌
```javascript
function App() {
  const [specialists, setSpecialists] = useState([]);
  const [activeSpecialists, setActiveSpecialists] = useState([]);

  useEffect(() => {
    fetchSpecialists();
  }, []);

  async function fetchSpecialists() {
    const response = await fetch('/api/specialists');
    const data = await response.json();
    setSpecialists(data);
    // ❌ Remove: Initialize active specialists
    setActiveSpecialists(data.map(s => s.id));
  }

  return (
    <ChatWindow 
      specialists={specialists}
      activeSpecialists={activeSpecialists}  // ❌ Remove
      onActiveSpecialistsChange={setActiveSpecialists}  // ❌ Remove
    />
  );
}
```

#### New Code ✅
```javascript
function App() {
  const [specialists, setSpecialists] = useState([]);

  useEffect(() => {
    fetchSpecialists();
  }, []);

  async function fetchSpecialists() {
    const response = await fetch('/api/specialists');
    const data = await response.json();
    setSpecialists(data);
    // All specialists always enabled - no tracking needed ✓
  }

  return (
    <ChatWindow specialists={specialists} />
  );
}
```

---

## Styling Updates

### Old CSS ❌
```css
.specialist-badge {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 8px 12px;
  border-radius: 20px;
  color: white;
  font-size: 12px;
  animation: fadeOut 1s ease-in-out;
}

/* Animation for dropped specialists */
@keyframes fadeOut {
  from { opacity: 1; transform: scale(1); }
  to { opacity: 0; transform: scale(0.8); }
}
```

### New CSS ✅
```css
.specialist-tabs {
  display: flex;
  gap: 8px;
  border-bottom: 2px solid #e0e0e0;
  padding-bottom: 10px;
}

.specialist-tabs button {
  padding: 8px 16px;
  border: none;
  background: transparent;
  cursor: pointer;
  font-weight: 500;
  border-bottom: 3px solid transparent;
  transition: all 0.3s ease;
}

.specialist-tabs button.active {
  color: #667eea;
  border-bottom-color: #667eea;
}

.specialist-card {
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  padding: 16px;
  margin-bottom: 12px;
  background: #f9f9f9;
}

.specialist-card h4 {
  margin-top: 0;
  color: #667eea;
}
```

---

## Testing Checklist

After updating your frontend:

- [ ] `npm run dev` starts without errors
- [ ] GET `/api/specialists` returns list of specialists
- [ ] POST `/api/chat` request has no `active_specialists` field
- [ ] POST `/api/chat` response contains `specialist_responses` object
- [ ] Chat message sends and displays response
- [ ] Multiple specialist responses display correctly
- [ ] No console errors about undefined `activeSpecialists`
- [ ] No console errors about undefined `droppedSpecialists`

---

## Example: Complete Updated Chat Hook

```javascript
// hooks/useChat.js
import { useState, useCallback } from 'react';

export function useChat() {
  const [messages, setMessages] = useState([]);
  const [specialistResponses, setSpecialistResponses] = useState({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const sendMessage = useCallback(async (userMessage) => {
    setLoading(true);
    setError(null);

    try {
      const newMessages = [
        ...messages,
        { role: 'user', content: userMessage }
      ];

      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          messages: newMessages
          // No active_specialists - this is removed ✓
        })
      });

      if (!response.ok) {
        throw new Error(`API error: ${response.status}`);
      }

      const data = await response.json();

      setMessages([
        ...newMessages,
        { role: 'assistant', content: data.response }
      ]);

      setSpecialistResponses(data.specialist_responses || {});
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [messages]);

  const clearChat = useCallback(() => {
    setMessages([]);
    setSpecialistResponses({});
    setError(null);
  }, []);

  return {
    messages,
    specialistResponses,
    loading,
    error,
    sendMessage,
    clearChat
  };
}
```

---

## Summary of Changes

| Aspect | Old | New |
|--------|-----|-----|
| **Active Specialists** | Tracked per request | All enabled specialists always respond |
| **Specialist Selection** | Dynamic (Whisper Protocol) | Static (from agents_enabled.json) |
| **Request Format** | includes `active_specialists` | Simplified, no `active_specialists` |
| **Response Format** | Single response + lists | Primary response + `specialist_responses` dict |
| **View Options** | Badge list, dropdown | Tabbed, stacked, consensus, or grid |
| **LLM Calls** | N+1 | N |
| **API Complexity** | Higher | Lower |

---

## Rollback (If Needed)

If you need to revert to the old API:

1. **Keep current code**: Commit your changes first
2. **Check git history**: `git log` to find old commit
3. **Restore old backend**: `git reset --hard <old-commit>`
4. **Restore old frontend**: Revert your frontend changes

But we recommend staying with the new architecture - it's better in every way! 🚀

---

## Support

For questions about the migration:
1. Check [QUICKSTART.md](./QUICKSTART.md) for backend setup
2. Check [RAG_ARCHITECTURE.md](./RAG_ARCHITECTURE.md) for detailed docs
3. Run [test_rag_system.py](./test_rag_system.py) to verify backend
4. Review API responses with browser DevTools Network tab
