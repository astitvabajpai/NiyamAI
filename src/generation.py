"""
LLM generation: stream answers from Groq using retrieved context.
Produces highly refined, structured, and authoritative regulatory responses.
"""

import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
# Valid Groq model IDs as fallbacks (in order of preference)
FALLBACK_MODELS = ["llama-3.3-70b-versatile", "llama3-70b-8192", "mixtral-8x7b-32768", "llama3-8b-8192"]

SYSTEM_PROMPT = """You are NiyamAI, a specialized regulatory intelligence AI for Reserve Bank of India (RBI) notifications, master directions, and circulars.

Your goal is to deliver authoritative, meticulously structured, and actionable answers based EXCLUSIVELY on the provided RBI context.

Structure your response using this clean, professional layout:

### 📌 Summary
Provide a concise, direct answer in 1-2 sentences summarizing the core regulatory position or rule.

### 📋 Key Provisions & Regulatory Requirements
Break down the detailed rules using organized bullet points:
- Use bold lead-in phrases for distinct concepts (e.g., **Customer Due Diligence (CDD):**, **Document Verification:**, **Transaction Thresholds:**).
- Explicitly detail quantitative criteria, timelines, conditions, and procedures from the text.
- If procedural steps are described, number them sequentially.

### ⚖️ Scope & Compliance Details
- Highlight applicable regulated entities (e.g., Commercial Banks, NBFCs, Payment Aggregators), specific exemptions, mandatory timeframes, or operational restrictions if present in the context.

### 📖 References & Citations
- Cite the relevant document names, circulars, or master directions with page numbers (e.g., `[Master Direction - KYC, p. 12]`).

CRITICAL RULES:
1. Grounding: Rely ONLY on facts stated in the context. Never guess, assume, or fabricate regulatory provisions.
2. If the context does not contain sufficient information to answer the question, state: "The available RBI documents in the repository do not contain sufficient information to answer this specific question."
3. Keep descriptions crisp, high-density, and structured so the complete answer and references fit cleanly."""


def generate_answer(query: str, context_chunks: list[dict], stream: bool = True, history: list[dict] = None):
    """Generate an answer from retrieved context, optionally streaming."""
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    primary_model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

    # Build rich context blocks with document, section, and page metadata
    context_blocks = []
    for c in context_chunks:
        header = f"[Document: {c['doc_name']} | Page: {c['page']}"
        if c.get("section"):
            header += f" | Section: {c['section']}"
        header += "]"
        context_blocks.append(f"{header}\n{c['text']}")

    context_text = "\n\n---\n\n".join(context_blocks)
    user_message = f"Question: {query}\n\nContext:\n{context_text}"
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    if history:
        for turn in history[-4:]:
            if turn.get("role") in ["user", "assistant"] and turn.get("content"):
                messages.append({"role": turn["role"], "content": turn["content"]})

    messages.append({"role": "user", "content": user_message})

    models_to_try = [primary_model] + [m for m in FALLBACK_MODELS if m != primary_model]

    for model in models_to_try:
        try:
            if stream:
                stream_resp = client.chat.completions.create(
                    model=model,
                    messages=messages,
                    stream=True,
                    max_tokens=850,
                    timeout=30,
                )
                for chunk in stream_resp:
                    content = chunk.choices[0].delta.content
                    if content:
                        yield content
                return
            else:
                resp = client.chat.completions.create(
                    model=model,
                    messages=messages,
                    max_tokens=850,
                    timeout=30,
                )
                yield resp.choices[0].message.content or ""
                return
        except Exception as e:
            # If model not found or timeout/forbidden, try next fallback
            estr = str(e).lower()
            if any(kw in estr for kw in ("model_not_found", "does not exist", "timeout", "connect")):
                continue
            raise e
