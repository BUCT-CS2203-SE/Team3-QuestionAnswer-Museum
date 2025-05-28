import os
#配置环境变量
os.environ["LANGCHAIN_TRACING"] = "true"
os.environ["LANGSMITH_ENDPOINT"] = "https://api.smith.langchain.com"
os.environ["LANGSMITH_PROJECT"] = "KnowledgeAnswerRobot"
os.environ["LANGSMITH_API_KEY"] = "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"
os.environ["OPENAI_API_KEY"] = "sk-5734cc4199a54962840b55b1ab9080b5"
os.environ["OPENAI_API_BASE"] = "https://dashscope.aliyuncs.com/compatible-mode/v1/"

# Neo4j数据库连接配置
os.environ["NEO4J_URI"] = "neo4j+s://3575cdb1.databases.neo4j.io"
os.environ["NEO4J_USERNAME"] = "neo4j"
os.environ["NEO4J_PASSWORD"] = "P0xP5COpfVh6_NMQC1cLckfHIyIBVXpHVGbZHOeKM2Q"

from langchain_community.graphs import Neo4jGraph


graph = Neo4jGraph()

# 用查询语句载入电影信息

movies_query = """
LOAD CSV WITH HEADERS FROM 
'https://raw.githubusercontent.com/tomasonjo/blog-datasets/main/movies/movies_small.csv'
AS row
MERGE (m:Movie {id:row.movieId})
SET m.released = date(row.released),
    m.title = row.title,
    m.imdbRating = toFloat(row.imdbRating)
FOREACH (director in split(row.director, '|') | 
    MERGE (p:Person {name:trim(director)})
    MERGE (p)-[:DIRECTED]->(m))
FOREACH (actor in split(row.actors, '|') | 
    MERGE (p:Person {name:trim(actor)})
    MERGE (p)-[:ACTED_IN]->(m))
FOREACH (genre in split(row.genres, '|') | 
    MERGE (g:Genre {name:trim(genre)})
    MERGE (m)-[:IN_GENRE]->(g))
"""

graph.query(movies_query)

#更新刚刚新增的图谱内的图形模式信息
graph.refresh_schema()
print(graph.schema)

# 运行查询
from langchain.chains import GraphCypherQAChain
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(model="qwen-max", temperature=0)
chain = GraphCypherQAChain.from_llm(graph=graph, llm=llm, verbose=True,validate_cypher=True)
response = chain.invoke({"query": "What was the cast of the Casino?"})
