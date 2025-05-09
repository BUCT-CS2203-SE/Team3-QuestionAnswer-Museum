import getpass
import os
from langchain_openai import ChatOpenAI
os.environ["LANGCHAIN_TRACING"] = "true"
os.environ["LANGSMITH_ENDPOINT"] = "https://api.smith.langchain.com"
os.environ["LANGSMITH_PROJECT"] = "KnowledgeAnswerRobot"
os.environ["LANGSMITH_API_KEY"] = "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"
os.environ["OPENAI_API_KEY"] = "sk-5734cc4199a54962840b55b1ab9080b5"
os.environ["OPENAI_API_BASE"] = "https://dashscope.aliyuncs.com/compatible-mode/v1/"

from langchain_core.documents import Document
from langchain_community.embeddings import DashScopeEmbeddings

documents = [
    Document(
        page_content="Dogs are great companions, known for their loyalty and friendliness.",
        metadata={"source": "mammal-pets-doc"},
    ),
    Document(
        page_content="Cats are independent pets that often enjoy their own space.",
        metadata={"source": "mammal-pets-doc"},
    ),
    Document(
        page_content="Goldfish are popular pets for beginners, requiring relatively simple care.",
        metadata={"source": "fish-pets-doc"},
    ),
    Document(
        page_content="Parrots are intelligent birds capable of mimicking human speech.",
        metadata={"source": "bird-pets-doc"},
    ),
    Document(
        page_content="Rabbits are social animals that need plenty of space to hop around.",
        metadata={"source": "mammal-pets-doc"},
    ),
]
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings

embedding = DashScopeEmbeddings(
    model="text-embedding-v2",
    dashscope_api_key="sk-5734cc4199a54962840b55b1ab9080b5",
)
vectorstore = Chroma.from_documents(
    documents,
    embedding=embedding,
)





retriever = vectorstore.as_retriever(
    search_type="similarity",
    search_kwargs={"k": 1},
)


from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough

message = """
Answer this question using the provided context only.

{question}

Context:
{context}
"""

prompt = ChatPromptTemplate.from_messages([("human", message)])

rag_chain = {"context": retriever, "question": RunnablePassthrough()} | prompt | ChatOpenAI(model="qwen-max")
response = rag_chain.invoke("tell me about cats")