import boto3
from langchain_core.documents import Document
from opensearchpy import OpenSearch, RequestsHttpConnection, AWSV4SignerAuth, helpers


def _build_client(endpoint: str, region: str, service: str = "es") -> OpenSearch:
    """Create an OpenSearch client that signs requests with your AWS credentials."""
    credentials = boto3.Session().get_credentials()
    auth = AWSV4SignerAuth(credentials, region, service)
    host = endpoint.replace("https://", "").rstrip("/")
    return OpenSearch(
        hosts=[{"host": host, "port": 443}],
        http_auth=auth,
        use_ssl=True,
        verify_certs=True,
        connection_class=RequestsHttpConnection,
        pool_maxsize=20,
        timeout=60,
    )


class OpenSearchVectorStore:
    def __init__(self, endpoint: str, index_name: str, region: str,
                 service: str = "es", dimensions: int = 1024):
        self.client = _build_client(endpoint, region, service)
        self.index_name = index_name
        self.dimensions = dimensions
        self._ensure_index()

    def _ensure_index(self) -> None:
        """Create the index with a vector field if it doesn't exist yet."""
        if self.client.indices.exists(index=self.index_name):
            return
        body = {
            "settings": {"index": {"knn": True}},
            "mappings": {
                "properties": {
                    "content": {"type": "text"},
                    "embedding": {
                        "type": "knn_vector",
                        "dimension": self.dimensions,
                        "method": {"name": "hnsw", "engine": "faiss", "space_type": "innerproduct"},
                    },
                    "company": {"type": "keyword"},
                    "year": {"type": "keyword"},
                    "source_file": {"type": "keyword"},
                    "chunk_id": {"type": "integer"},
                }
            },
        }
        self.client.indices.create(index=self.index_name, body=body)
        print(f"Created index '{self.index_name}'")

    def upload_chunks(self, chunks: list[Document], embeddings,
                      company: str, year: str, source_file: str) -> None:
        """Embed chunks and store them. Old chunks for the same file are removed first."""
        self.client.delete_by_query(
            index=self.index_name,
            body={"query": {"term": {"source_file": source_file}}},
            refresh=True,
        )

        texts = [c.page_content for c in chunks]
        vectors = embeddings.embed_documents(texts)

        actions = [
            {
                "_op_type": "index",
                "_index": self.index_name,
                "_id": f"{source_file}-{i}",
                "_source": {
                    "content": text,
                    "embedding": vector,
                    "company": company,
                    "year": year,
                    "source_file": source_file,
                    "chunk_id": i,
                },
            }
            for i, (text, vector) in enumerate(zip(texts, vectors))
        ]
        helpers.bulk(
            self.client,
            actions,
            chunk_size=25,
            request_timeout=120,
            refresh=True,
        )
        print(f"Uploaded {len(actions)} chunks to '{self.index_name}'")


class Retriever:
    def __init__(self, client: OpenSearch, index_name: str, embeddings):
        self.client = client
        self.index_name = index_name
        self.embeddings = embeddings

    def search(self, query: str, company: str | None = None,
               year: int | str | None = None, k: int = 5) -> list[Document]:
        """Return the k chunks most similar to the query, optionally filtered."""
        vector = self.embeddings.embed_query(query)

        filters = []
        if company:
            filters.append({"term": {"company": company}})
        if year:
            filters.append({"term": {"year": str(year)}})

        knn = {"vector": vector, "k": k}
        if filters:
            knn["filter"] = {"bool": {"must": filters}}

        body = {
            "size": k,
            "query": {"knn": {"embedding": knn}},
            "_source": {"excludes": ["embedding"]},
        }
        hits = self.client.search(index=self.index_name, body=body)["hits"]["hits"]

        return [
            Document(
                page_content=h["_source"]["content"],
                metadata={
                    "company": h["_source"]["company"],
                    "year": h["_source"]["year"],
                    "source_file": h["_source"]["source_file"],
                    "chunk_id": h["_source"]["chunk_id"],
                    "score": h["_score"],
                },
            )
            for h in hits
        ]