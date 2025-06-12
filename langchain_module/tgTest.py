from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.prompts import MessagesPlaceholder, ChatPromptTemplate
from langchain_core.runnables import RunnableWithMessageHistory
from neo4j import GraphDatabase
from langchain_openai import ChatOpenAI
import os
from langchain_neo4j import Neo4jGraph
from dotenv import load_dotenv
import re

from main import with_message_history

load_dotenv()

# 初始化大语言模型
llm = ChatOpenAI(
    temperature=0,
    model="qwen-max",
    openai_api_key="sk-5734cc4199a54962840b55b1ab9080b5",
    openai_api_base="https://dashscope.aliyuncs.com/compatible-mode/v1/",
)

# 设置 Neo4j 凭据
os.environ["NEO4J_URI"] = "bolt://localhost:7687"
os.environ["NEO4J_USERNAME"] = "neo4j"
os.environ["NEO4J_PASSWORD"] = "Cs22032025"

# 建立连接
neo4j_driver = Neo4jGraph(database="museumsample")


def test_connection():
    try:
        result = neo4j_driver.query("RETURN 1 AS result")
        print("Neo4j连接成功") if result else print("Neo4j连接失败")
    except Exception as e:
        print(f"Neo4j连接失败: {str(e)}")


system_prompt = """
您是中国文物知识图谱的Cypher专家，数据库结构如下：

【节点标签】
- Artifact: name
- Artist: name（国籍，生卒年）
- Material: name
- Time: name（起始年份-结束年份）
- Museum: name

【关系类型】
(Artifact)-[:创作者为]->(Artist)
(Artifact)-[:位于]->(Museum)
(Artifact)-[:处于的年代]->(Time)
(Artifact)-[:材质为]->(Material)

【关键约束】
1. 必须返回文物名称：RETURN a.name AS artifact_name
2. 其他返回字段统一用AS附加信息（如：museum_name/time_info）
3. 所有查询必须包含文物节点（a）
4. 使用WHERE进行精确匹配

请生成Cypher查询语句：
- 如果用户问题是“某朝代有哪些文物”，请模糊匹配时间节点
- 如果用户问题是“某朝代有哪些文物”，只需返回文物名称（artifact_name）
- 回复格式要求：代码块形式，不要注释。
"""

cypher_prompt = ChatPromptTemplate(
    [
        ("system", system_prompt),
        MessagesPlaceholder(variable_name="history"),
        ("human", "{input}"),
    ]
)

cypher_chain = cypher_prompt | llm


def execute_cypher(query: str) -> list:
    try:
        result = neo4j_driver.query(query)
        return result
    except Exception as e:
        print(f"数据库查询错误: {str(e)}")
        return []


def refine_cypher(raw_cypher: str) -> str:
    cypher = re.sub(r"```\w*", "", raw_cypher).strip()

    # 移除多余空行
    cypher = re.sub(r"\n\s*\n", "\n", cypher)

    # 查找当前 RETURN 子句
    return_match = re.search(r"RETURN\s+(.+)", cypher, re.IGNORECASE)
    if return_match:
        return_fields = return_match.group(1)

        # 如果没有包含 artifact_name 字段，添加 a.name AS artifact_name
        if "artifact_name" not in return_fields:
            new_return_fields = f"a.name AS artifact_name, {return_fields}"
            cypher = re.sub(r"RETURN\s+.+", f"RETURN {new_return_fields}", cypher)
    else:
        # 如果没有 RETURN，补一个
        cypher += "\nRETURN a.name AS artifact_name"

    # 确保 MATCH 中的文物节点使用别名 a
    cypher = re.sub(r"MATCH\s*\(\w+:Artifact", "MATCH (a:Artifact", cypher)

    return cypher



def format_result(data: list) -> str:
    if not data:
        return "未找到相关记录"

    output = []
    for idx, item in enumerate(data, 1):
        artifact_name = item.get("artifact_name", "未知文物")

        # 仅有文物名称字段，直接列出名称
        if len(item) == 1:
            output.append(f"{idx}. {artifact_name}")
        else:
            # 否则构建完整自然语言描述
            descriptions = []
            for key in item:
                if key != "artifact_name":
                    value = item[key]
                    if "time" in key.lower():
                        descriptions.append(f"所处朝代：{value}")
                    elif "museum" in key.lower():
                        descriptions.append(f"收藏于：{value}")
                    elif "material" in key.lower():
                        descriptions.append(f"制作材质：{value}")
                    elif "artist" in key.lower():
                        descriptions.append(f"创作者：{value}")

            desc_str = f"{artifact_name}的" + "，".join(descriptions) if descriptions else f"{artifact_name}的基本信息"
            output.append(f"{idx}. {desc_str}")

    return "\n".join(output)


def process_question(question: str, history: BaseChatMessageHistory) -> tuple:
    with_message_history = RunnableWithMessageHistory(
        cypher_chain,
        lambda config: history,
        input_messages_key="input",
        history_messages_key="history",
    )
    response = with_message_history.invoke(
        {"input": question},
        config={"configurable": {"session_id": "dummy"}},
    )
    raw_cypher = response.content.strip()
    final_cypher = refine_cypher(raw_cypher)
    print(f"生成的Cypher语句：\n{final_cypher}")
    return final_cypher, execute_cypher(final_cypher)


def get_artifact_answer(question: str, history: BaseChatMessageHistory) -> str:
    try:
        question = question.encode("utf-8", errors="replace").decode("utf-8")
        cypher, result = process_question(question, history)
        answer = format_result(result)
        return answer
    except Exception as e:
        return f"处理问题时出错: {str(e)}"


if __name__ == "__main__":
    test_connection()
    print("""\n文物知识问答系统
输入问题查询文物信息，支持自然语言提问
输入 exit 或 quit 退出系统""")

    while True:
        try:
            user_input = input("\n请输入问题：").strip()
            if user_input.lower() in ["exit", "quit"]:
                print("感谢使用，再见！")
                break
            if not user_input:
                print("问题不能为空！")
                continue

            import chatHistory

            chat_service = chatHistory.ChatHistory()
            history = chat_service._get_session_history(1, 0)
            answer = get_artifact_answer(user_input, history)
            print("\n=== 查询结果 ===")
            print(answer)

        except KeyboardInterrupt:
            print("\n操作已终止")
            break
        except Exception as e:
            print(f"系统错误: {str(e)}")