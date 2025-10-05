import logging
import json
import os
import time
from fastapi import Request, HTTPException

logger = logging.getLogger(__name__)

@app.post("/api/generate_automation")
async def generate_automation(request: Request):
    """Generate automation with conversation context support."""
    logger.info("=== generate_automation endpoint called ===")
    
    try:
        data = await request.json()
        logger.info(f"Request data received: {json.dumps(data, indent=2)}")
    except Exception as e:
        logger.error(f"Failed to parse request JSON: {e}")
        raise HTTPException(status_code=400, detail="Invalid JSON in request body")
    
    prompt = data.get("prompt")
    conversation_history = data.get("conversation_history", [])
    
    logger.info(f"Prompt: {prompt}")
    logger.info(f"Conversation history length: {len(conversation_history)}")
    
    if not prompt:
        logger.warning("No prompt provided")
        raise HTTPException(status_code=400, detail="Prompt is required")
    
    try:
        # Build the full prompt with conversation context
        full_context = ""
        if conversation_history:
            logger.info("Building context from conversation history")
            full_context = "Previous conversation:\n"
            for i, msg in enumerate(conversation_history):
                role = "User" if msg["role"] == "user" else "Assistant"
                full_context += f"{role}: {msg['content']}\n\n"
                logger.debug(f"History message {i}: {role}")
            full_context += f"User: {prompt}"
        else:
            logger.info("No conversation history, using prompt directly")
            full_context = prompt
        
        logger.info(f"Full context length: {len(full_context)} characters")
        logger.debug(f"Full context: {full_context[:200]}...")  # First 200 chars
        
        # Generate automation using existing service
        logger.info("Calling automation_service.generate_automation...")
        result = await automation_service.generate_automation(full_context)
        logger.info("automation_service.generate_automation completed")
        logger.info(f"Result keys: {list(result.keys())}")
        logger.debug(f"Result: {json.dumps(result, indent=2)}")
        
        response_data = {
            "full_response": result.get("full_response", ""),
            "yaml": result.get("yaml", ""),
            "summary": result.get("summary", "")
        }
        
        logger.info(f"Sending response with full_response length: {len(response_data['full_response'])}")
        logger.info(f"YAML present: {bool(response_data['yaml'])}")
        
        return response_data
        
    except Exception as e:
        logger.error(f"Error generating automation: {e}", exc_info=True)
        return {
            "full_response": f"Error: {str(e)}",
            "error": str(e)
        }


@app.get("/api/chat/history")
async def get_chat_history(request: Request):
    """Get persisted chat history from Home Assistant storage."""
    logger.info("=== get_chat_history endpoint called ===")
    
    try:
        # Load from Home Assistant storage
        storage_path = "/data/chat_history.json"
        
        if not os.path.exists(storage_path):
            logger.info("No chat history found")
            return {"messages": []}
        
        with open(storage_path, 'r') as f:
            data = json.load(f)
        
        # Check if data is too old (7 days)
        timestamp = data.get("timestamp", 0)
        age_days = (time.time() - timestamp) / (60 * 60 * 24)
        
        if age_days > 7:
            logger.info(f"Chat history is {age_days:.1f} days old, clearing")
            os.remove(storage_path)
            return {"messages": []}
        
        messages = data.get("messages", [])
        logger.info(f"Loaded {len(messages)} messages from storage")
        
        return {"messages": messages}
        
    except Exception as e:
        logger.error(f"Error loading chat history: {e}", exc_info=True)
        return {"messages": [], "error": str(e)}


@app.post("/api/chat/history")
async def save_chat_history(request: Request):
    """Save chat history to Home Assistant storage."""
    logger.info("=== save_chat_history endpoint called ===")
    
    try:
        data = await request.json()
        messages = data.get("messages", [])
        
        logger.info(f"Saving {len(messages)} messages to storage")
        
        # Save to Home Assistant storage
        storage_path = "/data/chat_history.json"
        storage_data = {
            "messages": messages,
            "timestamp": time.time()
        }
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(storage_path), exist_ok=True)
        
        with open(storage_path, 'w') as f:
            json.dump(storage_data, f, indent=2)
        
        logger.info("Chat history saved successfully")
        return {"success": True}
        
    except Exception as e:
        logger.error(f"Error saving chat history: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/chat/history")
async def clear_chat_history(request: Request):
    """Clear persisted chat history."""
    logger.info("=== clear_chat_history endpoint called ===")
    
    try:
        storage_path = "/data/chat_history.json"
        
        if os.path.exists(storage_path):
            os.remove(storage_path)
            logger.info("Chat history cleared")
        
        return {"success": True}
        
    except Exception as e:
        logger.error(f"Error clearing chat history: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))