# app/api.py
import os
os.environ["OPENAI_API_KEY"] = "sk-mock-key-for-local-testing"
os.environ["CREWAI_DISABLE_TELEMETRY"] = "true"
os.environ["OTEL_SDK_DISABLED"] = "true"

import json
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field
from governance import AIGovernanceManager
from budget_guard import BudgetExceededError
from app.crew_old import run_crew_with_session
from logger import logger
from cache_manager import ResponseCacheManager
import chromadb
from sentence_transformers import SentenceTransformer

app = FastAPI(
    title="Cred Domain Support Agent API",
    description="Production-grade financial support backend with RAG, multi-agent orchestration, and structured logging.",
    version="1.0.0"
)

class AskRequest(BaseModel):
    query: str = Field(..., description="The user's support question or request.")
    session_id: Optional[str] = Field("default_session", description="Unique session identifier for conversational memory.")

class AddDocumentRequest(BaseModel):
    document_id: str = Field(..., description="Unique ID for the new policy document.")
    text: str = Field(..., description="Policy content text (2-5 sentences).")

PROJECT_ROOT = Path(__file__).resolve().parent
if PROJECT_ROOT.name in ["app", "tools"]:
    PROJECT_ROOT = PROJECT_ROOT.parent
CHROMA_DIR = PROJECT_ROOT / "chroma_db"

@app.post("/ask", summary="Synchronous Support Endpoint with Caching & Governance")
def ask_endpoint(payload: AskRequest):
    logger.info(f"Received /ask request for session_id={payload.session_id} with query: {payload.query}")
    
    # 1. Check Response Cache
    cached_result = ResponseCacheManager.get(payload.query)
    if cached_result:
        logger.info(f"CACHE HIT for query: '{payload.query}'")
        return {
            "success": True,
            "cached": True,
            "cache_telemetry": {
                "status": "CACHE_HIT",
                "latency_delta_seconds": 0.001
            },
            "answer": cached_result["response"]["answer"],
            "metadata": cached_result["response"].get("metadata", {})
        }

    # 2. Cache Miss: Execute governed request
    start_time = time.time()
    try:
        def agent_executor(sanitized_q: str, sess_id: str):
            res = run_crew_with_session(user_query=sanitized_q, session_id=sess_id)
            if isinstance(res, str):
                return {"success": True, "answer": res, "context": ""}
            return res

        governed_response = AIGovernanceManager.process_governed_request(
            user_query=payload.query,
            session_id=payload.session_id or "default_session",
            execution_callback=agent_executor
        )

        execution_latency = round(time.time() - start_time, 3)
        
        # Add cache telemetry for the miss
        governed_response["cached"] = False
        governed_response["cache_telemetry"] = {
            "status": "CACHE_MISS",
            "execution_latency_seconds": execution_latency
        }

        # Store in cache for subsequent hits
        ResponseCacheManager.set(payload.query, governed_response)

        logger.info(f"CACHE MISS & STORE for query: '{payload.query}' in {execution_latency}s")
        return governed_response

    except BudgetExceededError as bee:
        raise bee
    except Exception as e:
        logger.error(f"Error processing /ask request: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/add-document", summary="Dynamic Policy Ingestion")
def add_document_endpoint(payload: AddDocumentRequest):
    logger.info(f"Received request to add document ID: {payload.document_id}")
    try:
        client = chromadb.PersistentClient(path=str(CHROMA_DIR))
        model = SentenceTransformer("all-MiniLM-L6-v2")
        collection = client.get_collection("cred_kb_sentence_based")
        
        embedding = model.encode([payload.text]).tolist()
        collection.upsert(
            documents=[payload.text],
            embeddings=embedding,
            ids=[payload.document_id]
        )
        
        logger.info(f"Successfully indexed document ID: {payload.document_id}")
        return {
            "success": True,
            "message": f"Document '{payload.document_id}' successfully added and indexed.",
            "document_id": payload.document_id
        }
    except Exception as e:
        logger.error(f"Failed to index document {payload.document_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to index document: {str(e)}")

@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    await websocket.accept()
    session_id = f"ws_session_{id(websocket)}"
    logger.info(f"WebSocket client connected with session ID: {session_id}")
    
    try:
        await websocket.send_json({
            "sender": "system",
            "message": "Connected to Cred Support WebSocket. Send your query."
        })
        
        while True:
            data = await websocket.receive_text()
            logger.info(f"WebSocket received message for {session_id}")
            query = data
            try:
                parsed = json.loads(data)
                if isinstance(parsed, dict) and "query" in parsed:
                    query = parsed["query"]
                    if "session_id" in parsed:
                        session_id = parsed["session_id"]
            except Exception:
                pass

            result = run_crew_with_session(user_query=query, session_id=session_id)
            await websocket.send_json({
                "sender": "agent",
                "response": result
            })
            
    except WebSocketDisconnect:
        logger.info(f"WebSocket client disconnected gracefully for session: {session_id}")
    except Exception as e:
        logger.error(f"WebSocket error in session {session_id}: {str(e)}")
        try:
            await websocket.send_json({"error": str(e)})
        except Exception:
            pass

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="127.0.0.1", port=8000, reload=False)
