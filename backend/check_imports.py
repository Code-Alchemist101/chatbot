import langchain.chains
print(dir(langchain.chains))
try:
    from langchain.chains import create_history_aware_retriever
    print("Found create_history_aware_retriever in langchain.chains")
except ImportError:
    print("Not found in langchain.chains")

try:
    from langchain.chains.history_aware_retriever import create_history_aware_retriever
    print("Found in langchain.chains.history_aware_retriever")
except ImportError:
    print("Not found in langchain.chains.history_aware_retriever")
