import os
from typing import List, Dict, Any, AsyncGenerator
import asyncio
from neo4j import GraphDatabase
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.runnables import ConfigurableFieldSpec


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


class ChatHistory:
    """聊天服务类，提供与LLM交互和历史记录管理的功能"""

    DB_CONFIG = {
        "host": "101.43.234.152",
        "user": "SE2025",
        "password": "Cs22032025",
        "db": "quizhistory",
        "port": 3306
    }

    def __init__(self, init_env=True):
        """初始化聊天服务"""
        if init_env:
            os.environ["LANGCHAIN_TRACING"] = "true"
            os.environ["LANGSMITH_ENDPOINT"] = "https://api.smith.langchain.com"
            os.environ["LANGSMITH_PROJECT"] = "KnowledgeAnswerRobot"
            os.environ["LANGSMITH_API_KEY"] = "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"
            os.environ["OPENAI_API_KEY"] = "sk-5734cc4199a54962840b55b1ab9080b5"
            os.environ["OPENAI_API_BASE"] = "https://dashscope.aliyuncs.com/compatible-mode/v1/"

        # 初始化模型和链
        self.model = ChatOpenAI(model="qwen-max")
        self.parser = StrOutputParser()

        # 创建提示模板
        self.prompt = ChatPromptTemplate([
            ("system", "Please respond in {language},{hint}"),
            MessagesPlaceholder(variable_name="history"),
            ("human", "{input}"),
        ])

        # 创建基础链
        self.chain = self.prompt | self.model | self.parser

        # 创建带历史记录的可运行链
        self.with_message_history = RunnableWithMessageHistory(
            self.chain,
            self._get_session_history,
            input_messages_key="input",
            history_messages_key="history",
            history_factory_config=[
                ConfigurableFieldSpec(id="user_id", annotation=str, name="User ID", default=None, is_shared=True),
                ConfigurableFieldSpec(id="session_id", annotation=str, name="Session ID", default=None, is_shared=True)
            ]
        )

        # 初始化知识图谱
        self.kg = KnowledgeGraph(
            uri="bolt://localhost:7687",  # 或你的远程地址
            user="neo4j",
            password="taoguan@20040326"
        )

        # 历史记录初始化
        self.history = {}

    def close(self):
        """关闭连接"""
        self.kg.close()

    def _get_session_history(self, user_id: str, session_id: str) -> List[str]:
        """获取历史记录"""
        session_key = (user_id, session_id)
        if session_key not in self.history:
            self.history[session_key] = []
        return self.history[session_key]

    def query_artwork_knowledge(self, artwork_name: str) -> str:
        """查询某个文物的知识信息（目前只返回同一作者的作品）"""
        related = self.kg.query_related_artworks_by_author(artwork_name)
        if not related:
            return f"没有找到与『{artwork_name}』相关的其他文物信息。"
        related_names = [r["name"] for r in related]
        return f"与『{artwork_name}』属于同一作者的文物有：{', '.join(related_names)}。"

    async def ask_about_artwork(
        self, user_input: str, artwork_name: str, user_id: str, session_id: str
    ) -> AsyncGenerator[str, None]:
        """处理文物相关问题并调用流式 LLM 响应"""
        kg_info = self.query_artwork_knowledge(artwork_name)
        async for chunk in self.stream_response(
            content=user_input,
            systeminput=kg_info,
            user_id=user_id,
            session_id=session_id
        ):
            yield chunk

    async def stream_response(
        self, content: str, systeminput: str, user_id: str, session_id: str
    ) -> AsyncGenerator[str, None]:
        """生成流式响应"""
        response = f"系统提示：{systeminput}\n用户问题：{content}\n"
        # 模拟分块响应流
        for i in range(0, len(response), 20):
            yield response[i:i+20]
        yield "\n【结束】"


async def example_usage():
    chat_service = ChatHistory()

    # 示例 1: 发送问题并查询文物相关信息
    user_input = "请问《清明上河图》的作者还画过哪些作品？"
    artwork_name = "清明上河图"
    user_id = "user123"
    session_id = "session1"

    async for chunk in chat_service.ask_about_artwork(
        user_input=user_input,
        artwork_name=artwork_name,
        user_id=user_id,
        session_id=session_id
    ):
        print(chunk, end='', flush=True)
    print()

    # 关闭服务
    chat_service.close()

if __name__ == "__main__":
    asyncio.run(example_usage())
