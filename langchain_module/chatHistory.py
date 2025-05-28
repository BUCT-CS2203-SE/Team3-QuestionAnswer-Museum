import asyncio
import os
from typing import List, Dict, Any, AsyncGenerator
import pymysql

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from langchain_core.messages import (
    SystemMessage,
    HumanMessage,
    AIMessage,
    BaseMessage,
    message_to_dict,
    messages_from_dict,
    trim_messages
)
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.runnables import RunnablePassthrough, ConfigurableFieldSpec
from requests import session

from main import MySQLChatMessageHistory


class ChatHistory:
    # MySQL数据库连接配置
    DB_CONFIG = {
        "host": "101.43.234.152",
        "user": "SE2025",
        "password": "Cs22032025",
        "db": "quizhistory",
        "port": 3306
    }

    def __init__(self, init_env=True):
        """初始化聊天服务

        Args:
            init_env: 是否初始化环境变量
        """
        if init_env:
            # 初始化环境变量
            os.environ["LANGCHAIN_TRACING"] = "true"
            os.environ["LANGSMITH_ENDPOINT"] = "https://api.smith.langchain.com"
            os.environ["LANGSMITH_PROJECT"] = "KnowledgeAnswerRobot"
            os.environ["LANGSMITH_API_KEY"] = "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"
            os.environ["OPENAI_API_KEY"] = "sk-5734cc4199a54962840b55b1ab9080b5"
            os.environ["OPENAI_API_BASE"] = "https://dashscope.aliyuncs.com/compatible-mode/v1/"

        # 初始化模型和链
        self.model = ChatOpenAI(model="qwen-max",temperature=0.1)
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
                ConfigurableFieldSpec(
                    id="user_id",
                    annotation=str,
                    name="User ID",
                    default=None,
                    is_shared=True,
                ),
                ConfigurableFieldSpec(
                    id="session_id",
                    annotation=str,
                    name="Session ID",
                    default=None,
                    is_shared=True,
                )
            ]
        )

    def _get_session_history(self, user_id: str, session_id: str):
        """获取指定用户和会话的聊天历史

        Args:
            user_id: 用户ID
            session_id: 会话ID

        Returns:
            聊天历史对象
        """
        return MySQLChatMessageHistory(
            user_id=user_id,
            session_id=session_id,
            connection_params=self.DB_CONFIG
        )

    def _send_session_history(self, user_id: str, session_id: str):
        """获取会话历史消息并返回"""
        history = MySQLChatMessageHistory(
            user_id=user_id,
            session_id=session_id,
            connection_params=self.DB_CONFIG
        )
        # 使用猴子补丁方式使对象只读
        history.add_message = lambda _: None
        return history

    def get_all_user_history(self, user_id: str) -> List[Dict[str, Any]]:
        """获取指定用户ID的所有聊天历史记录

        Args:
            user_id: 用户ID

        Returns:
            包含所有会话记录的列表，每个元素为一个会话的信息和消息内容
        """
        conn = pymysql.connect(**self.DB_CONFIG)
        try:
            # 首先获取该用户的所有会话ID
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT DISTINCT session_id FROM chat_history WHERE user_id = %s",
                    (user_id,)
                )
                session_ids = [row[0] for row in cursor.fetchall()]

            # 获取每个会话的所有消息
            all_history = []
            for session_id in session_ids:
                with conn.cursor(pymysql.cursors.DictCursor) as cursor:
                    cursor.execute(
                        "SELECT role, content, timestamp FROM chat_history WHERE user_id = %s AND session_id = %s ORDER BY timestamp",
                        (user_id, session_id)
                    )
                    messages = cursor.fetchall()

                    # 将会话信息和消息内容添加到结果中
                    all_history.append({
                        "session_id": session_id,
                        "messages": messages
                    })

            return all_history
        finally:
            conn.close()

    def stream_response(self, content: str, systeminput: str, user_id: str, session_id: str,
                      language: str = "Chinese") -> str:

        response = self.with_message_history.invoke(
                {
                    "input": content,  # 直接传入文本内容
                    "hint": "你是一个博物馆知识问答助手，名字是小博。以下是用户最新问题经过另一个Agent在知识图谱中查询后的形式结果：\n知识图谱直接提供的查询结果：\n"+systeminput+"\n\n\n\n重要提示：\n1. 你必须优先使用知识图谱中的信息来回答问题,\n2. 如果知识图谱中有相关信息，请基于这些信息并且进行润色之后你简单补充一下回答\n3. 只有在知识图谱查询结果显示'未找到相关记录'或为空时，才可以使用你的通用知识\n4. 回答时请明确指出信息来源（知识图谱或通用知识）\n5. 保持回答的连贯性和自然性，适当添加表情符号以贴近用户\n6.如果用户的输入不是博物馆知识型问题，请与他闲聊，不要使用查询结果，用你自己的知识库，保持轻松的语气。\n7.若你进行分点作答，在最后总结要点\n请基于以上要求回答问题。\n如果有结果，请用该结果回答用户最新的问题，若与对话历史有关联，请整合上下文，给出合理的回答。\n",
                    "language": language,
                },
                config={"configurable": {"session_id": session_id, "user_id": user_id}},
        )
        return response



class MySQLChatMessageHistory(BaseChatMessageHistory):
    """MySQL聊天历史存储类"""

    def __init__(self, user_id: str, session_id: str, connection_params: dict):
        """初始化MySQL聊天历史存储

        Args:
            user_id: 用户ID
            session_id: 会话ID
            connection_params: MySQL连接参数
        """
        self.user_id = user_id
        self.session_id = session_id
        self.connection_params = connection_params

    def _get_connection(self):
        """获取数据库连接"""
        return pymysql.connect(**self.connection_params)

    def add_message(self, message: BaseMessage) -> None:
        """添加一条消息到历史记录

        Args:
            message: 消息对象
        """
        conn = self._get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO chat_history (user_id, session_id, role, content) VALUES (%s, %s, %s, %s)",
                    (self.user_id, self.session_id, message.type.upper(), message.content)
                )
            conn.commit()
        finally:
            conn.close()

    def clear(self) -> None:
        """清除该用户会话的所有历史记录"""
        conn = self._get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    "DELETE FROM chat_history WHERE user_id = %s AND session_id = %s",
                    (self.user_id, self.session_id)
                )
            conn.commit()
        finally:
            conn.close()

    @property
    def messages(self) -> List[BaseMessage]:
        """获取历史消息

        Returns:
            消息列表
        """
        conn = self._get_connection()
        try:
            with conn.cursor(pymysql.cursors.DictCursor) as cursor:
                cursor.execute(
                    "SELECT role, content FROM chat_history WHERE user_id = %s AND session_id = %s ORDER BY id DESC LIMIT 6",
                    (self.user_id, self.session_id)
                )
                results = cursor.fetchall()
                # 因为是按时间戳降序获取的，需要反转以保持对话顺序
                results = list(reversed(results))

            messages_dicts = [{"type": row["role"].lower(), "data": {"content": row["content"]}} for row in results]
            return messages_from_dict(messages_dicts)
        finally:
            conn.close()


# 使用示例
def example_usage():
    # 创建聊天服务实例->django

    #初始化
    chat_service = ChatHistory()
    # 示例1: 获取用户历史
    #输入userId、sessionId
    userId = "1"
    sessionId = "0"


    #输出
    user_history = chat_service.get_all_user_history(userId)   #返回[{'session_id':'','messages':[{'role':'','content':'','timestamp':''},...]},...]
    print("User history:", user_history)   #仅测试可删去



    # 示例2： 发送消息并与最新历史记录连接->rag
    #输入user_input、userId、sessionId
    user_input = "龙造型鼻烟壶和龙形吊坠有什么共同点"       #用户的问题
    history = chat_service._send_session_history(userId, sessionId)     #userId和sessionId


    import chatArtifact
    system_input = chatArtifact.get_artifact_answer(user_input, history)  # 从Rag得到的答案

    # 输出
    response = chat_service.stream_response(
        content=user_input,
        systeminput=system_input,
        user_id=userId,
        session_id=sessionId,
        language="Chinese"
    )
    print("回复:", response)


if __name__ == "__main__":
    # 运行示例
    example_usage()