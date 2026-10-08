import os
from functools import lru_cache

from langchain_aws import BedrockEmbeddings


@lru_cache(maxsize=1)
def get_embeddings() -> BedrockEmbeddings:
    """One shared embeddings client, built once per process instead of per-call."""
    return BedrockEmbeddings(
        model_id=os.getenv("BEDROCK_EMBEDDING_MODEL_ID", "amazon.titan-embed-text-v2:0"),
        region_name=os.getenv("AWS_REGION", "us-east-1"),
        normalize=True,
    )