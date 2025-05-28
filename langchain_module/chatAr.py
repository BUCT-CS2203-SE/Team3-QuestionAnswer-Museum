from neo4j import GraphDatabase
from langchain_core.messages import SystemMessage

from chatHistory import ChatHistory


class CulturalQA:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def query_related_artifact(self, artifact_name: str) -> str:
        """
        查询与给定文物有关的其他文物及其关系。
        :param artifact_name: 文物名称，如 "清明上河图"
        :return: 查询结果字符串
        """
        query = """
        MATCH (a1)-[r]->(a2)
        WHERE a1.name = $name
        RETURN a1.name AS from_name, type(r) AS relation, a2.name AS to_name
        """
        with self.driver.session() as session:
            results = session.run(query, name=artifact_name)
            records = results.data()

        if not records:
            return f"未找到与文物\"{artifact_name}\"有关的知识图谱信息。"

        response_lines = ["知识图谱查询结果："]
        for record in records:
            response_lines.append(f"{record['from_name']} --[{record['relation']}]--> {record['to_name']}")
        return "\n".join(response_lines)


# 接入你的 ChatHistory
async def cultural_qa_with_neo4j():
    # 初始化聊天服务
    chat_service = ChatHistory()
    user_id = "user123"
    session_id = "3"
    user_input = "请告诉我清明上河图的相关信息"

    # 抽取文物名（可扩展为 NER）
    artifact_name = "清明上河图"

    # 查询 Neo4j
    neo4j_qa = CulturalQA(uri="bolt://localhost:7687", user="neo4j", password="taoguan@20040326")
    related_info = neo4j_qa.query_related_artifact(artifact_name)
    neo4j_qa.close()

    # 将图谱知识注入作为 system_input
    async for chunk in chat_service.stream_response(
            content=user_input,
            systeminput=related_info,
            user_id=user_id,
            session_id=session_id,
            language="Chinese"
    ):
        print(chunk, flush=True)


if __name__ == "__main__":
    import asyncio
    asyncio.run(cultural_qa_with_neo4j())