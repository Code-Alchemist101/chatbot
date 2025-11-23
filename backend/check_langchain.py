import langchain
print("LangChain version:", langchain.__version__)
print("LangChain dir:", dir(langchain))

try:
    import langchain.chains
    print("Imported langchain.chains")
except ImportError as e:
    print(f"Failed to import langchain.chains: {e}")

try:
    from langchain.chains import RetrievalQA
    print("Found RetrievalQA")
except ImportError:
    print("RetrievalQA not found")
