import asyncio
import getpass
import os
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from requests import session
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import SystemMessage, trim_messages, HumanMessage, AIMessage

from langchain_core.chat_history import (
    BaseChatMessageHistory,
    InMemoryChatMessageHistory,
)
from langchain_core.runnables.history import RunnableWithMessageHistory
from operator import itemgetter

from langchain_core.runnables import RunnablePassthrough, ConfigurableFieldSpec
os.environ["LANGCHAIN_TRACING"] = "true"
os.environ["LANGSMITH_ENDPOINT"] = "https://api.smith.langchain.com"
os.environ["LANGSMITH_PROJECT"] = "KnowledgeAnswerRobot"
os.environ["LANGSMITH_API_KEY"] = "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"
os.environ["OPENAI_API_KEY"] = "sk-5734cc4199a54962840b55b1ab9080b5"
os.environ["OPENAI_API_BASE"] = "https://dashscope.aliyuncs.com/compatible-mode/v1/"


model = ChatOpenAI(model="qwen-max")

# MySQL数据库连接配置
DB_CONFIG = {
    "host": "101.43.234.152",  # 数据库主机地址
    "user": "SE2025",    # 数据库用户名
    "password": "Cs22032025", # 数据库密码
    "db": "quizhistory",      # 数据库名
    "port": 3306                # 端口号，默认3306
}

# 创建MySQL聊天历史存储类
from langchain_core.messages import BaseMessage, message_to_dict, messages_from_dict
import pymysql
from typing import List

class MySQLChatMessageHistory(BaseChatMessageHistory):
    def __init__(self, user_id: str, session_id: str, connection_params: dict):
        self.user_id = user_id
        self.session_id = session_id
        self.connection_params = connection_params

    def _get_connection(self):
        return pymysql.connect(**self.connection_params)

    def add_message(self, message: BaseMessage) -> None:
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
        conn = self._get_connection()
        try:
            with conn.cursor(pymysql.cursors.DictCursor) as cursor:
                cursor.execute(
                    "SELECT role, content FROM chat_history WHERE user_id = %s AND session_id = %s ORDER BY id",
                    (self.user_id, self.session_id)
                )
                results = cursor.fetchall()

            messages_dicts = [{"type": row["role"].lower(), "data": {"content": row["content"]}} for row in results]
            return messages_from_dict(messages_dicts)
        finally:
            conn.close()
parser = StrOutputParser()

# 创建消息存储结构：{user_id: {session_id: InMemoryChatMessageHistory}}
message_store = {}

def get_session_history(user_id: str, session_id: str) -> BaseChatMessageHistory:
        # 使用MySQL存储聊天历史
        return MySQLChatMessageHistory(user_id=user_id, session_id=session_id, connection_params=DB_CONFIG)

trimmer = trim_messages(
    max_tokens=50,
    strategy="last",
    token_counter=ChatOpenAI(model="gpt-4"),#本地调用
    include_system=True,
    allow_partial=False,
    start_on="human",
)

messages = [#这里保存历史消息
    SystemMessage(content="you're a good assistant"),
    HumanMessage(content="hi! I'm bob"),
    AIMessage(content="hi!"),
    HumanMessage(content="I like vanilla ice cream"),
    AIMessage(content="nice"),
    HumanMessage(content="whats 2 + 2"),
    AIMessage(content="4"),
    HumanMessage(content="thanks"),
    AIMessage(content="no problem!"),
    HumanMessage(content="having fun?"),
    AIMessage(content="yes!"),
]
prompt = ChatPromptTemplate(
    [
        ("system", "You're a helpful assistant.Please respond in {language}"),
        MessagesPlaceholder(variable_name="history"),
        ("human", "{input}"),
    ]
)


chain = (
    RunnablePassthrough.assign(history=itemgetter("history") | trimmer)
    | prompt
    | model
    | parser
)

with_message_history = RunnableWithMessageHistory(
    chain,
    get_session_history,
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

async def stream_response(content:str):
    async for chunk in with_message_history.astream(
        {
            "input":  [HumanMessage(content=content)],#最新消息填入口
            "history": messages,
            "language": "Chinese",
        },
        config={"configurable": {"session_id": "session1", "user_id": "user123"}},
    ):
        print(chunk, end="|", flush=True)
if __name__ == "__main__":
    asyncio.run(stream_response('我叫什么名字'))


