from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import os
import groq

router = APIRouter()

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: list[ChatMessage]

@router.post("/chat")
def chat_with_bot(req: ChatRequest):
    try:
        g_client = groq.Groq(api_key=os.getenv("ROCKETRIDE_GROQ_KEY"))
        system_msg = {"role": "system", "content": "You are the Bid-Factory Assistant, helping with B2B RFP proposals. Answer questions concisely."}
        
        # Prepare messages
        api_msgs = [system_msg]
        for m in req.messages:
            api_msgs.append({"role": m.role, "content": m.content})
            
        completion = g_client.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=api_msgs,
            temperature=0.7,
            max_tokens=600,
        )
        return {"reply": completion.choices[0].message.content}
    except Exception as e:
        print("Chatbot Error:", e)
        raise HTTPException(status_code=500, detail="Failed to connect to AI.")
