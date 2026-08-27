# src/generator.py
import requests
import json
import os
import torch
from src.config import (
    LLM_PROVIDER, OLLAMA_BASE_URL, OLLAMA_MODEL, 
    TRANSFORMERS_MODEL
)

# Global variables for caching local transformers model to avoid reloading on every query
local_model = None
local_tokenizer = None

def load_local_model():
    """Load local Hugging Face model for generation if provider is 'transformers'."""
    global local_model, local_tokenizer
    if local_model is not None:
        return local_model, local_tokenizer
        
    print(f"Loading local LLM '{TRANSFORMERS_MODEL}' using HuggingFace transformers...")
    from transformers import AutoTokenizer, AutoModelForCausalLM
    
    local_tokenizer = AutoTokenizer.from_pretrained(TRANSFORMERS_MODEL)
    
    # Determine device: GPU if available, else CPU
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Loading model on device: {device}")
    
    # Load model (use 16-bit or 8-bit precision to save GPU memory on GTX 1650)
    torch_dtype = torch.float16 if device == "cuda" else torch.float32
    local_model = AutoModelForCausalLM.from_pretrained(
        TRANSFORMERS_MODEL,
        torch_dtype=torch_dtype,
        device_map="auto"
    )
    print("Local LLM model loaded successfully.")
    return local_model, local_tokenizer

def generate_answer_ollama(prompt, system_prompt):
    """Generate answer using local Ollama instance."""
    url = f"{OLLAMA_BASE_URL}/api/generate"
    headers = {"Content-Type": "application/json"}
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "system": system_prompt,
        "stream": False,
        "options": {
            "temperature": 0.2
        }
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        data = response.json()
        return data.get("response", "")
    except Exception as e:
        print(f"Ollama generation failed: {e}")
        # Return fallback error explanation
        return f"Error connecting to Ollama at {OLLAMA_BASE_URL}. Ensure Ollama is running and '{OLLAMA_MODEL}' model is pulled."

def generate_answer_transformers(prompt, system_prompt):
    """Generate answer using local Transformers model."""
    try:
        model, tokenizer = load_local_model()
        
        # Combine system prompt and prompt in conversational format
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]
        
        text = tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True
        )
        
        device = "cuda" if torch.cuda.is_available() else "cpu"
        model_inputs = tokenizer([text], return_tensors="pt").to(device)
        
        with torch.no_grad():
            generated_ids = model.generate(
                model_inputs.input_ids,
                max_new_tokens=512,
                temperature=0.2,
                do_sample=True,
                top_p=0.9,
                pad_token_id=tokenizer.eos_token_id
            )
            
        generated_ids = [
            output_ids[len(input_ids):] for input_ids, output_ids in zip(model_inputs.input_ids, generated_ids)
        ]
        
        response = tokenizer.batch_decode(generated_ids, skip_special_tokens=True)[0]
        return response
    except Exception as e:
        print(f"Transformers generation failed: {e}")
        return f"Error running local Transformers model: {e}"

def generate_answer_api(prompt, system_prompt):
    """Generate answer using API (Gemini API / OpenRouter / OpenAI) as fallback."""
    gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if gemini_key:
        print("Using Gemini API for generation fallback...")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash:generateContent?key={gemini_key}"
        headers = {"Content-Type": "application/json"}
        payload = {
            "contents": [{
                "parts": [{
                    "text": f"{system_prompt}\n\nUser Question:\n{prompt}"
                }]
            }],
            "generationConfig": {
                "temperature": 0.2
            }
        }
        try:
            res = requests.post(url, headers=headers, json=payload, timeout=30)
            res.raise_for_status()
            data = res.json()
            return data["candidates"][0]["content"]["parts"][0]["text"]
        except Exception as e:
            print(f"Gemini API fallback failed: {e}")
            
    # Check if OpenAI key is present
    openai_key = os.getenv("OPENAI_API_KEY")
    if openai_key:
        print("Using OpenAI API for generation fallback...")
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {openai_key}"
        }
        payload = {
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.2
        }
        try:
            res = requests.post(url, headers=headers, json=payload, timeout=30)
            res.raise_for_status()
            data = res.json()
            return data["choices"][0]["message"]["content"]
        except Exception as e:
            print(f"OpenAI API fallback failed: {e}")
            
    return None

def format_context(chunks):
    """Format retrieved document chunks with clear visual indicators for LLM citation."""
    formatted_chunks = []
    citations_map = {}
    
    for i, chunk in enumerate(chunks, 1):
        filename = chunk["source"]
        page = chunk["page_number"]
        cite_key = f"[{filename}, Page {page}]"
        
        # Add to citations mapping for easy reference lookup
        citations_map[cite_key] = {
            "source": filename,
            "page_number": page,
            "content_preview": chunk["content"][:150] + "..."
        }
        
        chunk_text = f"--- Source {i}: {cite_key} ---\n{chunk['content']}\n"
        formatted_chunks.append(chunk_text)
        
    return "\n".join(formatted_chunks), citations_map

def generate_rag_response(query, retrieved_chunks):
    """Main generation logic: builds prompt, queries LLM provider, returns answer & citations."""
    if not retrieved_chunks:
        return {
            "answer": "No relevant legal documents could be retrieved from the database to answer your question.",
            "citations": []
        }
        
    context_str, citations_map = format_context(retrieved_chunks)
    
    system_prompt = (
        "You are an expert Legal Awareness AI assistant helping ordinary citizens understand legal information.\n"
        "Your task is to answer the user's question accurately and objectively, based ONLY on the provided context sections.\n"
        "Rules:\n"
        "1. Strictly ground your answer in the provided context. If the context does not contain the answer, say so. Do not speculate.\n"
        "2. Keep the explanation clear, accessible, and in plain English (avoid unnecessary legalese).\n"
        "3. You MUST cite your sources inside the answer using the exact source keys like [a2019-35.pdf, Page X] where the information is used.\n"
        "4. Include a disclaimer at the very end stating that this information is for educational/awareness purposes and does not constitute formal legal advice."
    )
    
    prompt = (
        f"Context documents:\n"
        f"=================================\n"
        f"{context_str}\n"
        f"=================================\n\n"
        f"User Question: {query}\n\n"
        f"Please provide your answer below, citing the pages using [Filename, Page X] keys:"
    )
    
    # Try API fallbacks first if they are configured (since they provide high quality and speed)
    response_text = generate_answer_api(prompt, system_prompt)
    
    if not response_text:
        # If API keys are not available, use the configured local provider
        if LLM_PROVIDER == "ollama":
            response_text = generate_answer_ollama(prompt, system_prompt)
        elif LLM_PROVIDER == "transformers":
            response_text = generate_answer_transformers(prompt, system_prompt)
        else:
            response_text = f"Invalid LLM provider configured: {LLM_PROVIDER}"
            
    # Extract citations actually used in the text
    used_citations = []
    for key, info in citations_map.items():
        if key in response_text:
            used_citations.append({
                "citation_key": key,
                "source": info["source"],
                "page_number": info["page_number"]
            })
            
    return {
        "answer": response_text,
        "citations": used_citations
    }
