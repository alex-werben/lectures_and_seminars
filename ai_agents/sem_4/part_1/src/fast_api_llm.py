from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from transformers import AutoTokenizer, AutoModelForCausalLM
import torch
import uvicorn
from typing import Optional
from contextlib import asynccontextmanager


# Global variables for model and tokenizer
model = None
tokenizer = None


def load_model():
   """Load the model and tokenizer"""
   global model, tokenizer
  
   model_id = "./models/Llama-3.2-1B-Instruct"
   tokenizer = AutoTokenizer.from_pretrained(model_id)


   model = AutoModelForCausalLM.from_pretrained(
       model_id,
       torch_dtype=torch.float16,
       device_map="cuda" if torch.cuda.is_available() else "cpu"
   )


   if tokenizer.pad_token is None:
       tokenizer.pad_token = tokenizer.eos_token
   if model.config.pad_token_id is None:
       model.config.pad_token_id = model.config.eos_token_id


@asynccontextmanager
async def lifespan(app: FastAPI):
   """Handle startup and shutdown events"""
   # Startup
   print("Loading model...")
   load_model()
   print("Model loaded successfully!")
   yield
   # Shutdown (if needed)
   print("Shutting down...")


# Initialize FastAPI app with lifespan
app = FastAPI(title="Text Generation API", version="1.0.0", lifespan=lifespan)


# Pydantic models for request and response
class TextGenerationRequest(BaseModel):
   text: str
   max_new_tokens: Optional[int] = 256
   temperature: Optional[float] = 0.1
   num_return_sequences: Optional[int] = 1


class TextGenerationResponse(BaseModel):
   generated_text: str
   input_token_count: int
   output_token_count: int
   total_token_count: int
   original_prompt: str


@app.get("/")
async def root():
   """Health check endpoint"""
   return {"message": "Text Generation API is running"}


@app.post("/generate", response_model=TextGenerationResponse)
async def generate_text(request: TextGenerationRequest):
   """
   Generate text based on input prompt
   """
   try:
       if model is None or tokenizer is None:
           raise HTTPException(status_code=500, detail="Model not loaded")
      
       inputs = tokenizer(request.text, return_tensors="pt").to(model.device)
       input_token_count = inputs['input_ids'].shape[1]
      
       output_sequences = model.generate(
           **inputs,
           max_new_tokens=request.max_new_tokens,
           num_return_sequences=request.num_return_sequences,
           temperature=request.temperature,
           do_sample=True,
           pad_token_id=tokenizer.pad_token_id
       )

       total_token_count = output_sequences.shape[1]
       output_token_count = total_token_count - input_token_count
      
       generated_text = tokenizer.decode(output_sequences[0], skip_special_tokens=True)
      
       return TextGenerationResponse(
           generated_text=generated_text,
           input_token_count=input_token_count,
           output_token_count=output_token_count,
           total_token_count=total_token_count,
           original_prompt=request.text
       )
      
   except Exception as e:
       raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")


@app.get("/health")
async def health_check():
   """Check if model is loaded and ready"""
   if model is None or tokenizer is None:
       return {"status": "error", "message": "Model not loaded"}
   return {"status": "healthy", "message": "Model is loaded and ready"}


if __name__ == "__main__":
   import os
  
   script_name = os.path.splitext(os.path.basename(__file__))[0]
  
   uvicorn.run(
       f"{script_name}:app",
       host="localhost",
       port=8800,
       reload=True,
       log_level="info"
   )



