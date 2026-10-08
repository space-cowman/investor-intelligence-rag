import os
from functools import lru_cache
from typing import TypeVar

from dotenv import load_dotenv
from langchain_aws import ChatBedrockConverse
from pydantic import BaseModel

load_dotenv()

T = TypeVar("T", bound=BaseModel)


@lru_cache(maxsize=1)
def get_chat_model() -> ChatBedrockConverse:
    """One shared Bedrock chat client (Converse API)."""
    return ChatBedrockConverse(
        model=os.getenv("BEDROCK_CHAT_MODEL_ID", "us.amazon.nova-2-lite-v1:0"),
        region_name=os.getenv("AWS_REGION", "us-east-1"),
        temperature=0.0,
        max_tokens=2048,
    )


def get_structured_completion(prompt: str, response_model: type[T]) -> T:
    """Ask the LLM to return data that fits `response_model`."""
    return get_chat_model().with_structured_output(response_model).invoke(prompt)


def get_completion(prompt: str) -> str:
    """Plain text answer (used later by the chat/RAG answer chain)."""
    content = get_chat_model().invoke(prompt).content
    if isinstance(content, list):
        content = "".join(block.get("text", "") for block in content if isinstance(block, dict))
    return content