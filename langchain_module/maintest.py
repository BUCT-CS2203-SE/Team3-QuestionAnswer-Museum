import os
from langchain_neo4j import Neo4jGraph

# 设置 Neo4j 凭据

os.environ["NEO4J_URI"] = "bolt://localhost:7687"
os.environ["NEO4J_USERNAME"] = "neo4j"
os.environ["NEO4J_PASSWORD"] = "Cs22032025"

# 建立连接
graph = Neo4jGraph(database="museumsample")

# 用户输入要查询的文物名称
artifact_name = input("请输入要查询的文物名称：")



# 查询文物的材质
query = """
MATCH (a:Artifact {name: $name})-[:材质为]->(m:Material)
RETURN a.name AS artifact, m.name AS material
"""
result = graph.query(query, params={"name": artifact_name})

# 打印结果
if result:
    for r in result:
        print(f"文物名称：{r['artifact']}，材质：{r['material']}")
else:
    print("未找到该文物的材质信息。")
#ssh root@101.43.234.152 -p 30000
#python3 /tmp/pycharm_project_99/maintest.py