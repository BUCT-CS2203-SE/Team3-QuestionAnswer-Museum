from neo4j import GraphDatabase
from typing import List, Dict

class KnowledgeGraph:
    """Neo4j 知识图谱查询类"""

    def __init__(self, uri: str, user: str, password: str):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def query_related_artworks_by_author(self, artwork: str) -> List[Dict]:
        """根据文物查询同一作者的其他文物"""
        query = """
        MATCH (a:Artwork {name: $artwork})-[:同一作者]-(related:Artwork)
        RETURN related.name AS name
        """
        with self.driver.session() as session:
            result = session.run(query, artwork=artwork)
            return [record.data() for record in result]
