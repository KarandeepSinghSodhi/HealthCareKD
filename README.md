# Medical Panel Chatbot

A multi-agent healthcare chatbot that simulates a panel of medical specialists. As a patient describes their symptoms, specialists dynamically evaluate the relevance of their domain and "drop out" if they are not needed. When only one specialist remains, the UI transitions to a personalized theme for that specialist.

## Highlights
- **Cost-Efficient "Whisper Protocol"**: Before running an expensive generation for a specialist response, the backend uses a lightweight LLM call to evaluate if a specialist is still relevant to the conversation ("YES/NO"). This significantly reduces API costs and improves response time.
- **Extensible Architecture**: Adding a new medical specialist is as simple as creating a new folder in `medical-panel-backend/agents/` containing a `config.json` and a `prompt.txt`. The backend auto-discovers these on startup.
- **Dynamic Theming**: The React frontend seamlessly transitions the entire color palette and theme to match the final remaining specialist.
- **Engaging UI**: Smooth avatar "drop-out" animations built with Framer Motion.

## Project Structure
- **/medical-panel-backend**: FastAPI server, Langchain agent routing logic, and specialist configurations.
- **/medical-panel-frontend**: Vite + React + TailwindCSS frontend application.

## Prerequisites
- Node.js (for the frontend)
- Python 3.10+ (for the backend)
- A Google Gemini API Key

## Setup & Installation

### 1. Backend Setup
```bash
cd medical-panel-backend
python -m venv venv
.\venv\Scripts\activate  # On Windows
# source venv/bin/activate # On Mac/Linux
pip install fastapi uvicorn pydantic langchain langchain-core langchain-community langchain-google-genai python-dotenv
```

Create a `.env` file in the `medical-panel-backend` directory and add your Google API key.
Be sure to start the **backend** from that same directory (e.g. `cd medical-panel-backend && uvicorn main:app --reload`)
so that the dotenv loader can find the file.  The server will print a warning if it
falls back to the mock model.
```env
GOOGLE_API_KEY=your_gemini_api_key_here
```
*(Note: If you don't provide an API key, or if the key isn't loaded correctly, the server
will print a warning on startup and run a Mock LLM for UI testing purposes.  Check the
console logs for "Using a mock LLM" to confirm.)*

Start the backend server:
```bash
uvicorn main:app --reload
```

### 2. Frontend Setup
```bash
cd medical-panel-frontend
npm install
npm run dev
```

Navigate to `http://localhost:5173` in your browser.  If the page is blank or
the chat window never appears, open the browser devtools and look for console
errors or failed network requests to `/api/specialists` – this usually means the
backend is not running or CORS is misconfigured.  The frontend now also displays
a "Loading specialists..." message while it waits for the API, which should help
diagnose connectivity problems.

## Adding a New Specialist
To add a new specialist (e.g., an Allergist):
1. Navigate to `medical-panel-backend/agents/`
2. Create a new folder named `allergist`
3. Inside `allergist`, create `config.json`:
   ```json
   {
       "name": "Allergist",
       "theme": "allergy",
       "colors": {
           "primary": "emerald-500",
           "background": "emerald-50",
           "text": "emerald-900"
       },
       "avatar": "allergist.png"
   }
   ```
4. Inside `allergist`, create a `prompt.txt` with their system instructions.
5. (Optional) Add an `allergist.png` avatar to `medical-panel-frontend/public/avatars/`.
6. Restart the backend server. The UI will automatically detect and include the new specialist!

## Built With
- **Frontend**: React, Vite, TailwindCSS, Framer Motion, Lucide-React
- **Backend**: Python, FastAPI, Langchain, Google Generative AI (Gemini)
