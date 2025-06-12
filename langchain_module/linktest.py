from neo4j import GraphDatabase

# 替换为你的用户名和密码
URI = "bolt://host.docker.internal:7687"
USER = "neo4j"
PASSWORD = "Cs22032025"  # 你在 Neo4j Browser 登录用的密码

driver = GraphDatabase.driver(URI, auth=(USER, PASSWORD))

def test_connection():
    with driver.session(database="museumsample") as session:
        result = session.run("MATCH (n) RETURN count(n) AS node_count")
        print("Total nodes:", result.single()["node_count"])

test_connection()
driver.close()
