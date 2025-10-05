import logging
import json
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