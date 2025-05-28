import asyncio

from langchain_core.messages import SystemMessage, HumanMessage

from chatHistory import ChatHistory

# 使用示例
async def example_usage():
    # 创建聊天服务实例->django

    # 初始化
    chat_service = ChatHistory()
    # 示例1: 获取用户历史
    # 输入userId、sessionId
    userId = "user123"
    sessionId = "1"

    # 输出
    user_history = chat_service.get_all_user_history(
        userId)  # 返回[{'session_id':'','messages':[{'role':'','content':'','timestamp':''},...]}]
    print("User history:", user_history)  # 仅测试可删去

    # 示例2: 发送消息并获取流式响应->django
    # 输入user_input、system_input
    user_input = "你好，我有改名过吗，我原名叫什么"  # 用户的问题
    system_input = "答案是张择端"  # 从Rag得到的答案

    # 输出(流式响应)
    async for chunk in chat_service.stream_response(
            content=user_input,
            systeminput=system_input,
            user_id=userId,
            session_id=sessionId
    ):
        print(chunk, flush=True)  # 输出流式字符串

    # 示例3： 发送消息并与最新历史记录连接->rag
    # 输入user_input、userId、sessionId
    user_input = "你能告诉我一些关于Python的信息吗？"  # 用户的问题
    history = chat_service._get_session_history(userId, sessionId)  # userId和sessionId

    # 输出
    messages_with_history = [SystemMessage(content=system_input)] + history.messages + [HumanMessage(
        content=user_input)]  # 返回要注入rag的消息列表[SystemMessage(content='',...),...,HumanMessage(content='',...)]
    print(messages_with_history)  # 仅测试可删去


if __name__ == "__main__":
    # 运行示例
    asyncio.run(example_usage())