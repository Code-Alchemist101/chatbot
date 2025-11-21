import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough

load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_INDEX = os.getenv("PINECONE_INDEX")

if not GOOGLE_API_KEY:
    raise ValueError("Missing GOOGLE_API_KEY in .env")
if not PINECONE_API_KEY or not PINECONE_INDEX:
    raise ValueError("Missing PINECONE_API_KEY or PINECONE_INDEX in .env")

# Initialize Embeddings
embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001", google_api_key=GOOGLE_API_KEY)

# Initialize Pinecone VectorStore
vector_store = PineconeVectorStore(
    index_name=PINECONE_INDEX,
    embedding=embeddings,
    pinecone_api_key=PINECONE_API_KEY
)

# Initialize LLM
llm = ChatGoogleGenerativeAI(model="gemini-pro", google_api_key=GOOGLE_API_KEY, temperature=0.7)

# RAG Prompt
template = """Answer the question based only on the following context:
{context}

Question: {question}
"""
prompt = ChatPromptTemplate.from_template(template)

def format_docs(docs):
    return "\n\n".join(doc.page_content for doc in docs)

# RAG Chain
rag_chain = (
    {"context": vector_store.as_retriever() | format_docs, "question": RunnablePassthrough()}
    | prompt
    | llm
    | StrOutputParser()
)

def get_answer(question):
    try:
        return rag_chain.invoke(question)
    except Exception as e:
        return f"Error generating answer: {e}"
