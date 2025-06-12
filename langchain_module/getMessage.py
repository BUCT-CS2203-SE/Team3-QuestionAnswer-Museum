from neo4j import GraphDatabase

def list_labels(tx):
    query = "CALL db.labels()"
    result = tx.run(query)
    return [record["label"] for record in result]

# 连接数据库
driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "Cs22032025"))
with driver.session() as session:
    labels = session.execute_read(list_labels)
    print("所有节点标签:", labels)


def inspect_label_properties(tx, label):
        query = f"MATCH (n:{label}) RETURN n LIMIT 5"
        result = tx.run(query)
        return [dict(record["n"]) for record in result]


# 示例：检查标签为 "Person" 的节点属性
label_to_inspect = "Title"
with driver.session() as session:
        sample_data = session.execute_read(inspect_label_properties, label_to_inspect)
        print(f"标签 '{label_to_inspect}' 的示例属性:", sample_data)

def list_relationship_types(tx):
    query = "CALL db.relationshipTypes()"
    result = tx.run(query)
    return [record["relationshipType"] for record in result]

with driver.session() as session:
    rel_types = session.execute_read(list_relationship_types)
    print("所有关系类型:", rel_types)


def inspect_relationship(tx, rel_type):
    query = f"""
    MATCH (a)-[r:{rel_type}]->(b)
    RETURN labels(a) AS start_labels, labels(b) AS end_labels
    LIMIT 1
    """
    result = tx.run(query)
    return [{"start": record["start_labels"], "end": record["end_labels"]} for record in result]

# 示例：检查关系类型为 "LIVES_IN" 的结构
rel_to_inspect = "LIVES_IN"
with driver.session() as session:
    rel_structure = session.execute_read(inspect_relationship, rel_to_inspect)
    print(f"关系 '{rel_to_inspect}' 的结构:", rel_structure)


def count_entities(tx):
    # 统计所有标签的节点数量
    node_count_query = """
    MATCH (n)
    RETURN labels(n) AS label, count(n) AS count
    """
    node_counts = list(tx.run(node_count_query))

    # 统计所有关系的数量
    rel_count_query = """
    MATCH ()-[r]->()
    RETURN type(r) AS type, count(r) AS count
    """
    rel_counts = list(tx.run(rel_count_query))

    return {"nodes": node_counts, "relationships": rel_counts}


with driver.session() as session:
    counts = session.execute_read(count_entities)
    print("节点统计:", counts["nodes"])
    print("关系统计:", counts["relationships"])


import pandas as pd

# 生成标签属性摘要
label_summary = []
for label in labels:
    with driver.session() as session:
        prop_query = f"""
        MATCH (n:{label})
        WITH keys(n) AS properties
        RETURN DISTINCT properties
        LIMIT 1
        """
        properties = session.run(prop_query).single()["properties"]
        label_summary.append({"Label": label, "Properties": properties})

df_labels = pd.DataFrame(label_summary)
print("\n节点标签属性摘要:")
print(df_labels)