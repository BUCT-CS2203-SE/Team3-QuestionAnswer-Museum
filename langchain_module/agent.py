# Import relevant functionality
import os
from langchain_openai import ChatOpenAI
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent
from langchain_core.tools import tool
from langchain_community.graphs import Neo4jGraph
from langchain_core.prompts import ChatPromptTemplate
import asyncio

os.environ["TAVILY_API_KEY"] = "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"
os.environ["LANGCHAIN_TRACING"] = "true"
os.environ["LANGSMITH_ENDPOINT"] = "https://api.smith.langchain.com"
os.environ["LANGSMITH_PROJECT"] = "KnowledgeAnswerRobot"
os.environ["LANGSMITH_API_KEY"] = "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"
os.environ["OPENAI_API_KEY"] = "sk-5734cc4199a54962840b55b1ab9080b5"
os.environ["OPENAI_API_BASE"] = "https://dashscope.aliyuncs.com/compatible-mode/v1/"
os.environ["NEO4J_URI"] = "neo4j+s://3575cdb1.databases.neo4j.io"
os.environ["NEO4J_USERNAME"] = "neo4j"
os.environ["NEO4J_PASSWORD"] = "P0xP5COpfVh6_NMQC1cLckfHIyIBVXpHVGbZHOeKM2Q"


# 连接知识图谱数据库
graph = Neo4jGraph(
)

# 创建生成Cypher查询的工具
@tool
def generate_cypher_query(user_input: str) -> str:
    """根据用户输入生成Cypher查询语句"""
    # 使用模型从用户输入中提取关键字并生成Cypher查询
    template = """
    基于以下用户输入，提取关键实体和关系，并生成一个有效的Neo4j Cypher查询语句。
    
    用户输入: {input}
    
    仅返回一个有效的Cypher查询语句，不要包含其他解释。
    """
    prompt = ChatPromptTemplate.from_template(template)
    cypher_chain = prompt | ChatOpenAI(model="qwen-max")
    cypher_query = cypher_chain.invoke({"input": user_input})
    return cypher_query

# 创建执行Cypher查询的工具
@tool
def query_knowledge_graph(cypher_query: str) -> str:
    """执行Cypher查询语句获取知识图谱中的信息"""
    try:
        result = graph.query(cypher_query)
        return str(result)
    except Exception as e:
        return f"查询执行错误: {str(e)}"

# Create the agent
memory = MemorySaver()
model = ChatOpenAI(model="qwen-max")
search = TavilySearchResults(max_results=2)
tools = [generate_cypher_query, query_knowledge_graph, search]
agent_executor = create_react_agent(model, tools, checkpointer=memory)

# Use the agent
async def stream_response(
    messages: dict, config: dict
) -> None:
    async for chunk in agent_executor.astream(messages, config):
        print(chunk, end="|", flush=True)

async def main():
    config = {"configurable": {"thread_id": "abc123"}}
    await stream_response({"messages":[HumanMessage(content="查询关于人工智能的基本概念")]}, config)
    await stream_response({"messages":[HumanMessage(content="深度学习和机器学习有什么区别？")]}, config)

# 运行异步主函数
if __name__ == "__main__":
    asyncio.run(main())

'''
async for event in agent_executor.astream_events(
    {"messages": [HumanMessage(content="whats the weather in sf?")]}, version="v1"
):
    kind = event["event"]
    if kind == "on_chain_start":
        if (
            event["name"] == "Agent"
        ):  # Was assigned when creating the agent with `.with_config({"run_name": "Agent"})`
            print(
                f"Starting agent: {event['name']} with input: {event['data'].get('input')}"
            )
    elif kind == "on_chain_end":
        if (
            event["name"] == "Agent"
        ):  # Was assigned when creating the agent with `.with_config({"run_name": "Agent"})`
            print()
            print("--")
            print(
                f"Done agent: {event['name']} with output: {event['data'].get('output')['output']}"
            )
    if kind == "on_chat_model_stream":
        content = event["data"]["chunk"].content
        if content:
            # Empty content in the context of OpenAI means
            # that the model is asking for a tool to be invoked.
            # So we only print non-empty content
            print(content, end="|")
    elif kind == "on_tool_start":
        print("--")
        print(
            f"Starting tool: {event['name']} with inputs: {event['data'].get('input')}"
        )
    elif kind == "on_tool_end":
        print(f"Done tool: {event['name']}")
        print(f"Tool output was: {event['data'].get('output')}")
        print("--")
'''