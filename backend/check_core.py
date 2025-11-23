import langchain_core
print("langchain_core version:", langchain_core.__version__)
print("langchain_core dir:", dir(langchain_core))

try:
    from langchain_core.runnables import RunnablePassthrough, RunnableLambda
    print("Found RunnablePassthrough")
except ImportError:
    print("RunnablePassthrough not found")

try:
    from langchain_core.output_parsers import StrOutputParser
    print("Found StrOutputParser")
except ImportError:
    print("StrOutputParser not found")
