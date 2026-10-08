import shutil
from pathlib import Path

from fastapi import APIRouter, File, UploadFile

from ingestion.embeddings import get_embeddings
from ingestion.ingest_documents import get_vector_store, ingest_document

router = APIRouter()


@router.post("/upload")
def upload_document(file: UploadFile = File(...)):
    upload_dir = Path("data/raw_pdfs")
    upload_dir.mkdir(parents=True, exist_ok=True)
    file_path = upload_dir / file.filename

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Run ingestion AFTER the file is fully written and closed
    ingest_document(
        pdf_path=str(file_path),
        embeddings=get_embeddings(),
        vector_store=get_vector_store(),
    )

    return {"message": "Document uploaded successfully", "file_name": file.filename}