from datetime import datetime, timezone, timedelta
from app.core.config import get_generation_model, get_gemini_client

_DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
_MONTHS = [
    "", "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"
]


def get_wib_formatted_date() -> str:
    """Return current date formatted in English locale with WIB (UTC+7) timezone."""
    wib_tz = timezone(timedelta(hours=7))
    now_wib = datetime.now(wib_tz)
    day_name = _DAYS[now_wib.weekday()]
    month_name = _MONTHS[now_wib.month]
    return f"{day_name}, {month_name} {now_wib.day}, {now_wib.year}"


def build_prompt(question: str, chunks: list[str]) -> str:
    """Build an augmented prompt combining contextual document chunks, system guidelines, and user question."""
    formatted_date = get_wib_formatted_date()
    context = "\n\n".join(chunks)

    return f"""You are an AI assistant that answers questions ONLY based on the provided document context.

Current date context: Today is {formatted_date} (WIB timezone).
Use this information to interpret relative time references in the user's question, such as "this year", "last year", "last month", "yesterday", etc.

MANDATORY RULES:
1. Use ONLY the data from the "Context" below — do not invent information or use external knowledge.
2. If the data is not in the context, respond with "I cannot find this information in the document."
3. For questions that require comparison or finding the highest/lowest values (maximum/minimum/most/least):
   - Read ALL available data in the context carefully.
   - Compare ALL relevant values before determining the answer.
   - List the value of EACH relevant entry to make the comparison transparent.
   - State the final answer clearly.
4. For tabular data (tables/spreadsheets):
   - Read each row systematically before concluding.
   - Treat dashes ("-") or empty cells as 0 or no activity.
5. Response format: use **bold** for key terms/names, bullet lists for enumeration, and standard paragraphs for explanation.

Context:
{context}

Question: {question}

Answer:"""


def generate_answer(prompt: str) -> str:
    """Generate final answer using Groq (primary) with Gemini fallback.
    
    - Manual document path: always uses Groq for narrative generation.
    - Falls back to Gemini if groq_api_key is not yet configured in config_store.
    """
    try:
        from app.services.groq_client import groq_generate
        return groq_generate(
            prompt=prompt,
            system="You are an AI assistant for PT Terminal Petikemas Surabaya (TPS). Respond in a clear, professional, and helpful manner."
        )
    except Exception as groq_err:
        # Fallback to Gemini if Groq is not configured or fails
        import logging
        logging.getLogger(__name__).warning(
            f"[generation] Groq failed ({groq_err}), falling back to Gemini."
        )
        client = get_gemini_client()
        response = client.models.generate_content(
            model=get_generation_model(), contents=prompt
        )
        return response.text
