# from functools import lru_cache

# from fastapi import APIRouter, HTTPException
# from pydantic import BaseModel

# from ingestion.embeddings import get_embeddings
# from ingestion.ingest_documents import get_vector_store
# from llm.bedrock_llm import get_completion
# from vectorstore.opensearch_store import Retriever

# router = APIRouter()


# class ChatRequest(BaseModel):
#     question: str
#     company: str | None = None
#     year: int | None = None


# @lru_cache(maxsize=1)
# def get_retriever() -> Retriever:
#     """Create the retriever once and reuse it across requests."""
#     store = get_vector_store()
#     return Retriever(store.client, store.index_name, get_embeddings())


# @router.post("/chat")
# def chat(request: ChatRequest):
#     try:
#         docs = get_retriever().search(
#             query=request.question,
#             company=request.company,
#             year=request.year,
#             k=8,
#         )
#         context = "\n\n".join(doc.page_content for doc in docs)

#         prompt = (
#             "You are an expert financial analyst. Use the following context from corporate reports "
#             "to answer the user's question. If the context does not contain relevant information, "
#             "politely indicate that you do not have enough data.\n\n"
#             f"Context:\n{context}\n\nUser Question: {request.question}\n\nAnswer:"
#         )

#         return {"answer": get_completion(prompt)}
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))

from functools import lru_cache

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from database.save_metrics import get_metrics
from ingestion.embeddings import get_embeddings
from ingestion.ingest_documents import get_vector_store
from llm.bedrock_llm import get_completion
from vectorstore.opensearch_store import Retriever

router = APIRouter()


class ChatRequest(BaseModel):
    question: str
    company: str | None = None
    year: int | None = None


@lru_cache(maxsize=1)
def get_retriever() -> Retriever:
    store = get_vector_store()
    return Retriever(store.client, store.index_name, get_embeddings())


def detect_company(question: str, known_companies: set[str]) -> str | None:
    """If the user names a company we have data for, use it as a filter."""
    q = question.lower()
    for name in known_companies:
        if name.lower() in q:
            return name
    return None


def format_kpis(rows: list[dict]) -> str:
    """Turn saved KPI rows from Aurora into compact text for the prompt."""
    blocks = []
    for r in rows[:5]:
        blocks.append(
            f"{r['company']} FY{r['year']}:\n"
            f"- Revenue: {r['revenue']}\n"
            f"- Net income: {r['net_income']}\n"
            f"- Operating income: {r['operating_income']}\n"
            f"- Operating cash flow: {r['cash_flow']}\n"
            f"- Total assets: {r['total_assets']}\n"
            f"- Total liabilities: {r['total_liabilities']}\n"
            f"- Top risks: {(r['risk_factors'] or '').replace(chr(10), '; ')}\n"
            f"- Growth drivers: {(r['growth_drivers'] or '').replace(chr(10), '; ')}"
        )
    return "\n\n".join(blocks) or "None available."


def build_prompt(question: str, kpi_text: str, excerpts: str) -> str:
    return f"""You are a financial analyst assistant answering questions about company annual reports.

Rules:
- Use ONLY the facts in "Structured KPIs" and "Report excerpts". If the answer is not there, say so in one sentence.
- Start with a direct 1-2 sentence answer, then at most 5 short bullet points with the key facts.
- Quote figures exactly as written, with units and fiscal year.
- Use **bold** for key numbers. Do not use headings, horizontal rules, a conclusion section, or offers to help further.
- Keep the answer under 180 words unless the user asks for more detail.

Structured KPIs (extracted from the reports):
{kpi_text}

Report excerpts:
{excerpts}

Question: {question}

Answer:"""


@router.post("/chat")
def chat(request: ChatRequest):
    try:
        all_metrics = get_metrics()
        company = request.company or detect_company(
            request.question, {m["company"] for m in all_metrics}
        )
        year = request.year

        kpi_rows = [
            m for m in all_metrics
            if (company is None or m["company"] == company)
            and (year is None or m["year"] == year)
        ]

        docs = get_retriever().search(query=request.question, company=company, year=year, k=10)
        excerpts = "\n\n---\n\n".join(doc.page_content for doc in docs) or "None found."

        prompt = build_prompt(request.question, format_kpis(kpi_rows), excerpts)
        return {"answer": get_completion(prompt)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))