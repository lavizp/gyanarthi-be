import json
from langchain.embeddings import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain.text_splitter import RecursiveCharacterTextSplitter
import fitz  
import re
from langchain.chains import RetrievalQA
from langchain_groq import ChatGroq
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from langchain.memory import ConversationBufferMemory

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
        Uses Groq LLM to generate grammar, clarity, factual correctness scores and suggestions.
        """

        llm = ChatGroq(
            groq_api_key="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",
            model_name="llama-3.3-70b-versatile",
            temperature=0.2
        )

        system_prompt = """
        You are an academic writing reviewer.
        Analyze the given article and return JSON with:
        - grammar_score: float between 0 and 1
        - clarity_score: float between 0 and 1
        - factual_correctness: float between 0 and 1
        - suggestions: a short list of improvement suggestions
        Ensure the JSON is strictly in this format:
        {
          "grammar_score": <float>,
          "clarity_score": <float>,
          "factual_correctness": <float>,
          "suggestions": "<string>"
        }
        """

        user_prompt = f"""
        Title: {title}
        Content: {content}

        Research ID: {research_id or "None"}
        """

        response = await llm.ainvoke([
            {"role": "system", "content": system_prompt.strip()},
            {"role": "user", "content": user_prompt.strip()}
        ])
        try:
            return json.loads(response.content)
        except Exception:
            match = re.search(r"\{[\s\S]*\}", response.content)
            if match:
                return json.loads(match.group(0))
            # Final fallback
            return {
                "grammar_score": 0.0,
                "clarity_score": 0.0,
                "factual_correctness": 0.0,
                "suggestions": f"Could not parse Groq output: {response.content}"
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
            model_name="llama-3.3-70b-versatile",
            temperature=0.2
        )

        # Create system + user prompt template
        template = """
        You are a professional article generator.

        Goal:
        Write a clear, accurate, and well-structured article based on the user’s question and the provided context. Prioritize correctness, neutral tone, and readability.

        Instructions:
        - Use only the information in the Context. If something is unknown or not supported by the Context, state that it’s not available.
        - Answer the Question directly and comprehensively.
        - Organize the article into logical paragraphs. Use brief headings if helpful.
        - Maintain a professional, confident tone; avoid fluff and repetition.
        - Define terms briefly when first introduced.
        - Be precise with facts and avoid speculation.
        - Keep formatting simple: paragraphs, optional headings, and bullet points when summarizing.

        Context:
        {context}

        Question:
        {question}

        Output:
        A polished article (one paragraph) that addresses the Question using the Context, written for a general audience with a professional tone.
        Also, dont give any context. Give only the direct copyable asnwer.
        """

        prompt = PromptTemplate(
            template=template,
            input_variables=["context", "question"]
        )

        qa_chain = RetrievalQA.from_chain_type(
            llm=llm,
            chain_type="stuff",
            retriever=retriever,
            chain_type_kwargs={"prompt": prompt}
        )

        return qa_chain.run(query)
    
    def generate_chat_response(self, query: str, chat_history: list[str]):
            context_text = "\n".join(chat_history)
        
            llm = ChatGroq(
                groq_api_key="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",
                model_name="llama-3.3-70b-versatile",
                temperature=0.2
            )
        
            prompt = PromptTemplate(
                template="""
        You are a helpful chatbot.
        Conversation so far:
        {context}
        
        User: {question}
        Chatbot:""",
                input_variables=["context", "question"]
            )
        
            chain = LLMChain(llm=llm, prompt=prompt)
            return chain.run(context=context_text, question=query)
        

    