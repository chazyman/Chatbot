import os
import uuid
import base64

from contextlib import asynccontextmanager
from typing import Optional
from dotenv import load_dotenv

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from pydantic import BaseModel
from psycopg_pool import AsyncConnectionPool

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.graph import START, StateGraph, MessagesState
from langchain_core.messages import HumanMessage
from langchain_ollama import ChatOllama

import re

load_dotenv()

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://ollama:11435")
REMOVE_TOKENS = os.getenv("REMOVE_TOKENS", "True").lower() == "true"

# Regex to remove <think>...</think>
THINK_PATTERN = re.compile(r"<think>.*?</think>", re.DOTALL)


def remove_think_tokens(text: str) -> str:
    return re.sub(THINK_PATTERN, "", text)


model = ChatOllama(
    #model="llama3.1:8b",
    model="llava:7b",
    max_tokens=300,
    temperature=0,
    base_url=OLLAMA_URL,
    keep_alive=-1,
    timeout=300,
)


def call_model(state: MessagesState):
    response = model.invoke(state["messages"])
    if REMOVE_TOKENS:
        response.content = remove_think_tokens(response.content).strip()
    else:
        response.content = response.content.strip()
    return {"messages": [response]}


workflow = StateGraph(MessagesState)
workflow.add_node("agent", call_model)
workflow.add_edge(START, "agent")

DEFAULT_DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/postgres"


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("*** Setting up lifespan **** ")
    db_url = os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)
    async with AsyncConnectionPool(
        conninfo=db_url, kwargs={"autocommit": True}, max_size=20
    )  as pool:
        checkpointer = AsyncPostgresSaver(pool)
        await checkpointer.setup()

        app.state.graph = workflow.compile(checkpointer=checkpointer)
        try:
            yield
        finally:
            await pool.close()


app = FastAPI(lifespan=lifespan)

# CORS
origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Pydantic models for request/response
class CheckpointResponse(BaseModel):
    thread_id: str


class ChatRequest(BaseModel):
    thread_id: str
    message: str
    image: Optional[str] = None  # base64 encoded image string


class ChatResponse(BaseModel):
    answer: str

def is_base64(s: str) -> bool:
    """Check if string is base64 encoded"""
    try:
        # Try to decode the string
        if isinstance(s, str):
            base64.b64decode(s)
            return True
    except Exception:
        return False
    return False

@app.get("/checkpoint_id", response_model=CheckpointResponse)
async def get_checkpoint_id():
    new_id = str(uuid.uuid4())
    return CheckpointResponse(thread_id=new_id)


@app.post("/v1/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Empty message.")

    user_msg = HumanMessage(content=request.message)

    output = await app.state.graph.ainvoke(
        {"messages": [user_msg]},
        config={"configurable": {"thread_id": request.thread_id}},
    )

    if not output["messages"]:
        raise HTTPException(status_code=500, detail="No AI response returned.")

    ai_message = output["messages"][-1]
    return ChatResponse(answer=ai_message.content)

@app.post("/v2/chat", response_model=ChatResponse)
async def chat_vision(request: ChatRequest):
    print("*** Entering Chat Vision **** ")
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Empty message.")
    
    try:
        # Check if request contains an image
        if request.image:
            print("*** Image detected, using direct ChatOllama invocation ***")
            if not is_base64(request.image):
                raise HTTPException(status_code=400, detail="Invalid base64 image encoding")
            
            # Prepare multimodal content for image request
            content_parts = []
            
            # Add image
            image_part = {
                "type": "image_url",
                "image_url": f"data:image/jpeg;base64,{request.image}",
            }
            content_parts.append(image_part)
            
            # Add text
            text_part = {"type": "text", "text": request.message}
            content_parts.append(text_part)
            
            # Create multimodal message
            user_msg = HumanMessage(content=content_parts)
            
            # Use ChatOllama directly for image processing
            response = model.invoke([user_msg])
            
            if not response:
                raise HTTPException(status_code=500, detail="No AI response returned.")
            
            # Clean response if needed
            if REMOVE_TOKENS:
                response.content = remove_think_tokens(response.content).strip()
            else:
                response.content = response.content.strip()
                
            return ChatResponse(answer=response.content)
        
        else:
            # No image - use langgraph for conversation history
            print("*** Text-only request, using LangGraph workflow ***")
            user_msg = HumanMessage(content=request.message)
            
            output = await app.state.graph.ainvoke(
                {"messages": [user_msg]},
                config={"configurable": {"thread_id": request.thread_id}},
            )
            
            if not output["messages"]:
                raise HTTPException(status_code=500, detail="No AI response returned.")
            
            ai_message = output["messages"][-1]
            return ChatResponse(answer=ai_message.content)
    
    except Exception as e:
        print(f"Error in chat_vision: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing request: {str(e)}")