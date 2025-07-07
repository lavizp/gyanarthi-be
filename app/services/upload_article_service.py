import pdfplumber
from fastapi import FastAPI, UploadFile, Depends, HTTPException
from pymongo import MongoClient
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime
from sentence_transformers import SentenceTransformer
import faiss
import numpy as np
import asyncio


# FAISS USE NAGAR, USE QUADRANT

# Sentence-transformers embedding model (loads once)
embedder = SentenceTransformer('all-MiniLM-L6-v2')

# FAISS index for vector search (using inner product)
embedding_dim = 384  # embedding size of 'all-MiniLM-L6-v2'
index = faiss.IndexFlatIP(embedding_dim)

# Keep metadata in memory (map from vector id to metadata)
vector_id_to_meta = {}
current_vector_id = 0
lock = asyncio.Lock()  # To safely update shared vars async

def extract_text_from_pdf(file):
    text = ""
    with pdfplumber.open(file) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    return text


def embed_chunks(chunks: list[str]) -> list[list[float]]:
    return embedder.encode(chunks).tolist()


def chunk_text(text, max_len=500):
    paragraphs = text.split("\n")
    chunks = []
    current_chunk = ""
    for para in paragraphs:
        if len(current_chunk) + len(para) < max_len:
            current_chunk += para + " "
        else:
            chunks.append(current_chunk.strip())
            current_chunk = para + " "
    if current_chunk:
        chunks.append(current_chunk.strip())
    return chunks

async def search_article(query: str, top_k: int = 5):
    query_emb = await asyncio.to_thread(embedder.encode, [query], normalize_embeddings=True)
    query_emb = np.array(query_emb).astype('float32')

    if index.ntotal == 0:
        return {"results": []}

    # Search
    D, I = index.search(query_emb, top_k)  # distances and indices

    results = []
    for idx in I[0]:
        meta = vector_id_to_meta.get(idx)
        if meta:
            results.append(meta)

    return {"results": results}

# TODO: Results aaisakesi results bata filter hanera tanne
# More advanced concept: Re ranking
