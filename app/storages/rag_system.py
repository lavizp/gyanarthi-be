
from langchain.embeddings import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain.text_splitter import RecursiveCharacterTextSplitter
import fitz  
from langchain.chains import RetrievalQA
from langchain_groq import ChatGroq
class RAGSystem:
    def __init__(self):
        self.embeddins = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2"
        )
        self.vectordb = Chroma(
            persist_directory="./chroma_db",
            embedding_function=self.embeddins
        )
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=50
        )
    
    def get_full_text(self, pdf_path):
        doc = fitz.open(pdf_path)
        full_text = ""
        for page in doc:
            full_text += page.get_text()
        doc.close()
        return full_text

    def get_chunks(self, full_text):
        splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
        chunks = splitter.split_text(full_text)
        return chunks

    async def review_article(self, title: str, content: str, research_id: str = None) -> dict:
        """
        Return a dict compatible with AIFeedback:
        {
          "grammar_score": float (0-1),
          "clarity_score": float (0-1),
          "factual_correctness": float (0-1),
          "suggestions": str
        }
        """
        # TODO: Replace with a real LLM or heuristic-based review.
        # Example: run content through your QA pipeline, grammar checker, and
        # optionally compare with retrieved chunks from research_id for factuality.

        # Placeholder naive scoring:
        length = len(content.split())
        grammar_score = 0.85 if length > 50 else 0.6
        clarity_score = 0.8 if length > 100 else 0.65
        factual_correctness = 0.75  # Replace with retrieval-based check if research_id present

        suggestions = (
            "- Add an executive summary up top.\n"
            "- Use shorter paragraphs.\n"
            "- Include citations to specific pages from your source PDF.\n"
            "- Add a concluding section with 3–5 key takeaways."
        )

        return {
            "grammar_score": grammar_score,
            "clarity_score": clarity_score,
            "factual_correctness": factual_correctness,
            "suggestions": suggestions
    }
    def get_document_embeddings(self, chunks, user_id, research_id):
        docs = [
            {
                "page_content": c,
                "metadata": {
                    "user_id": str(user_id),
                    "research_id": str(research_id)
                }
            }
            for c in chunks
        ]
        self.vectordb.add_texts(texts=[d["page_content"] for d in docs], metadatas=[d["metadata"] for d in docs])
        # self.vectordb.persist()
        embedding_ids = [str(i) for i in range(len(docs))]  
        return embedding_ids
    
    def generate_answer(self, research_id: str, query: str):
        retriever = self.vectordb.as_retriever(
            search_kwargs={"k": 5, "filter": {"research_id": str(research_id)}}
        )
        llm = ChatGroq(
            groq_api_key="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",
            model_name="llama3-70b-8192",  # or llama3-70b-8192
            temperature=0.2
        )
        qa_chain = RetrievalQA.from_chain_type(
            llm=llm,
            chain_type="stuff",
            retriever=retriever
        )
        return qa_chain.run(query)