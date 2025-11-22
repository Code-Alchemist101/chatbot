import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_pinecone import PineconeVectorStore
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
import time

load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_INDEX = os.getenv("PINECONE_INDEX")

if not GOOGLE_API_KEY:
    raise ValueError("Missing GOOGLE_API_KEY in .env")
if not PINECONE_API_KEY or not PINECONE_INDEX:
    raise ValueError("Missing PINECONE_API_KEY or PINECONE_INDEX in .env")

# Initialize Embeddings
print("📥 Loading local embedding model (all-mpnet-base-v2)...")
embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-mpnet-base-v2")

# Initialize Pinecone VectorStore
vector_store = PineconeVectorStore(
    index_name=PINECONE_INDEX,
    embedding=embeddings,
    pinecone_api_key=PINECONE_API_KEY
)

# Initialize LLM
llm = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash", 
    google_api_key=GOOGLE_API_KEY, 
    temperature=0.3,
    max_output_tokens=1024
)

# RAG Prompt
template = """You are a helpful AI assistant for KL University. Answer the question based on the provided context with specific details.

Context from the university website:
{context}

Question: {question}

Instructions:
- Provide SPECIFIC and DETAILED information based on the context
- Include names, email addresses, phone numbers, and other precise details when available
- If the context doesn't contain relevant information, say "I don't have specific information about that in my knowledge base."
- Be concise but complete
- Use a friendly, professional tone
- Prioritize factual accuracy over general statements

Answer:"""

prompt = ChatPromptTemplate.from_template(template)

def format_docs(docs):
    """Format documents with source information"""
    if not docs:
        return "No relevant information found."
    
    formatted = []
    for i, doc in enumerate(docs, 1):
        source = doc.metadata.get('source', 'Unknown')
        title = doc.metadata.get('title', '')
        content = doc.page_content[:800]
        formatted.append(f"[Source {i}: {title}]\n{content}...")
    
    return "\n\n".join(formatted)

# Create retriever
retriever = vector_store.as_retriever(
    search_type="similarity",
    search_kwargs={"k": 8}
)

# RAG Chain
rag_chain = (
    {
        "context": retriever | format_docs, 
        "question": RunnablePassthrough()
    }
    | prompt
    | llm
    | StrOutputParser()
)

def get_answer(question, max_retries=3):
    """Get answer with retry logic"""
    retry_count = 0
    last_error = None
    
    while retry_count < max_retries:
        try:
            answer = rag_chain.invoke(question)
            
            if not answer or len(answer.strip()) < 10:
                return "I couldn't generate a complete answer. Please try asking in a different way."
            
            return answer.strip()
            
        except Exception as e:
            retry_count += 1
            last_error = e
            error_msg = str(e)
            
            print(f"RAG Error (attempt {retry_count}/{max_retries}): {type(e).__name__}")
            
            if "429" in error_msg or "quota" in error_msg.lower() or "rate" in error_msg.lower():
                if retry_count < max_retries:
                    wait_time = 2 ** retry_count
                    print(f"Rate limit hit, waiting {wait_time} seconds...")
                    time.sleep(wait_time)
                    continue
            
            if retry_count < max_retries:
                time.sleep(1)
    
    print(f"All retries failed. Last error: {last_error}")
    return "I'm currently experiencing technical difficulties. Please try again in a moment."