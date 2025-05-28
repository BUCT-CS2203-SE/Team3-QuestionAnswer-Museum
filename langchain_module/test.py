import os
from langchain_neo4j import Neo4jGraph

# 设置 Neo4j 凭据
os.environ["NEO4J_URI"] = "neo4j+s://3575cdb1.databases.neo4j.io"
os.environ["NEO4J_USERNAME"] = "neo4j"
os.environ["NEO4J_PASSWORD"] = "P0xP5COpfVh6_NMQC1cLckfHIyIBVXpHVGbZHOeKM2Q"

# 建立连接
graph = Neo4jGraph()

# 用户输入要查询的文物名称
artifact_name = input("请输入要查询的文物名称：")

# 执行查询
query = """
MATCH (a:Artifact {name: $name})-[:CREATED_BY]->(au:Author)
RETURN a.name AS artifact, au.name AS author
"""
result = graph.query(query, params={"name": artifact_name})

# 打印结果
if result:
    for row in result:
        print(f"{row['artifact']} 的作者是 {row['author']}")
else:
    print("未找到该文物的信息。")

