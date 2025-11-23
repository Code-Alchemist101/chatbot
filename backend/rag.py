import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_pinecone import PineconeVectorStore
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnablePassthrough, RunnableLambda, RunnableBranch
from langchain_core.output_parsers import StrOutputParser
from langchain_core.messages import HumanMessage, AIMessage
import time

load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_INDEX = os.getenv("PINECONE_INDEX")

if not GOOGLE_API_KEY:
    raise ValueError("Missing GOOGLE_API_KEY in .env")
if not PINECONE_API_KEY or not PINECONE_INDEX:
    raise ValueError("Missing PINECONE_API_KEY or PINECONE_INDEX in .env")

# Initialize LLM
llm = ChatGoogleGenerativeAI(
    model="gemini-1.5-flash",
    temperature=0.3,
    google_api_key=GOOGLE_API_KEY,
    convert_system_message_to_human=True
)

# Initialize Embeddings
embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

# Initialize Vector Store
vector_store = PineconeVectorStore(
    index_name=PINECONE_INDEX,
    embedding=embeddings
)

# --- Prompts ---

# 1. Contextualize Question Prompt (for history)
contextualize_q_system_prompt = """Given a chat history and the latest user question \
which might reference context in the chat history, formulate a standalone question \
which can be understood without the chat history. Do NOT answer the question, \
just reformulate it if needed and otherwise return it as is."""

contextualize_q_prompt = ChatPromptTemplate.from_messages([
    ("system", contextualize_q_system_prompt),
    MessagesPlaceholder("chat_history"),
    ("human", "{input}"),
])

# 2. QA Prompt
qa_system_prompt = """You are a helpful AI assistant. Answer the question based on the provided context with specific details.

Context from the website:
{context}

Instructions:
- Provide SPECIFIC and DETAILED information based on the context
- Include names, email addresses, phone numbers, and other precise details when available
- If the context doesn't contain relevant information, say "I don't have specific information about that in my knowledge base."
- Be concise but complete
- Use a friendly, professional tone
- Prioritize factual accuracy over general statements

Answer:"""

qa_prompt = ChatPromptTemplate.from_messages([
    ("system", qa_system_prompt),
    MessagesPlaceholder("chat_history"),
    ("human", "{input}"),
])

def format_docs(docs):
    return "\n\n".join(doc.page_content for doc in docs)

def get_rag_chain(namespace=None):
    """Create a RAG chain with history awareness using LCEL"""
    
    # 1. Retriever
    search_kwargs = {"k": 5}
    if namespace:
        search_kwargs["namespace"] = namespace
    
    retriever = vector_store.as_retriever(
        search_type="similarity",
        search_kwargs=search_kwargs
    )

    # 2. History Aware Retriever Chain
    # If history exists, reformulate question. Otherwise use input as is.
    history_aware_retriever = RunnableBranch(
        (
            lambda x: len(x.get("chat_history", [])) > 0,
            contextualize_q_prompt | llm | StrOutputParser() | retriever,
        ),
        (lambda x: x["input"]) | retriever,
    )

    # 3. QA Chain
    # We need to pass 'context' (retrieved docs) and 'input' and 'chat_history' to the QA prompt
    
    # Helper to get context from the history_aware_retriever
    # The input to this chain is a dict with 'input' and 'chat_history'
    
    rag_chain = (
        RunnablePassthrough.assign(
            context=history_aware_retriever | format_docs
        )
        | qa_prompt
        | llm
        | StrOutputParser()
    )
    
    return rag_chain

def get_answer(question, filters=None, namespace=None, chat_history=None):
    """Get answer using RAG chain"""
    if chat_history is None:
        chat_history = []
        
    # Convert dict history to LangChain messages if needed
    formatted_history = []
    for msg in chat_history:
        if isinstance(msg, dict):
            if msg.get('role') == 'user':
                formatted_history.append(HumanMessage(content=msg.get('content', '')))
            elif msg.get('role') == 'assistant':
                formatted_history.append(AIMessage(content=msg.get('content', '')))
        else:
            formatted_history.append(msg)

    try:
        chain = get_rag_chain(namespace)
        response = chain.invoke({
            "input": question,
            "chat_history": formatted_history
        })
        return response
    except Exception as e:
        print(f"Error in get_answer: {e}")
        return "I encountered an error while processing your request."

def get_answer_stream(question, filters=None, namespace=None, chat_history=None):
    """Get streaming answer using RAG chain"""
    if chat_history is None:
        chat_history = []
        
    formatted_history = []
    for msg in chat_history:
        if isinstance(msg, dict):
            if msg.get('role') == 'user':
                formatted_history.append(HumanMessage(content=msg.get('content', '')))
            elif msg.get('role') == 'assistant':
                formatted_history.append(AIMessage(content=msg.get('content', '')))
        else:
            formatted_history.append(msg)

    try:
        chain = get_rag_chain(namespace)
        for chunk in chain.stream({
            "input": question,
            "chat_history": formatted_history
        }):
            yield chunk
    except Exception as e:
        print(f"Error in get_answer_stream: {e}")
        yield f"Error: {str(e)}"