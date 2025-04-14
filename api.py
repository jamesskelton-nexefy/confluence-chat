from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Optional
import chat_with_confluence as cwc

app = FastAPI(title="Confluence Chat API")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    query: str
    conversation_history: Optional[List[Dict[str, str]]] = None

class ChatResponse(BaseModel):
    response: str
    conversation_history: List[Dict[str, str]]

@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        # Get relevant documents
        matches = cwc.hybrid_search(request.query)
        
        if not matches:
            raise HTTPException(status_code=404, detail="No relevant documentation found")
            
        # Format context with citations
        context, citation_map = cwc.format_context_with_citations(matches)
        
        # Generate response
        response = cwc.chat_with_context(
            request.query, 
            context, 
            citation_map, 
            request.conversation_history
        )
        
        # Update conversation history
        conversation_history = request.conversation_history or []
        conversation_history.append({"role": "user", "content": request.query})
        conversation_history.append({"role": "assistant", "content": response})
        
        # Trim history
        conversation_history = cwc.trim_conversation_history(conversation_history)
        
        return ChatResponse(
            response=response,
            conversation_history=conversation_history
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/clear-history")
async def clear_history():
    return {"conversation_history": cwc.clear_conversation_history()} 