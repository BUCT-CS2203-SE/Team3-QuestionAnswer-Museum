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
        # 简单测试查询
        result = neo4j_driver.query("RETURN 1 AS result")
        print("Neo4j连接成功") if result else print("Neo4j连接失败")
    except Exception as e:
        print(f"Neo4j连接失败: {str(e)}")

system_prompt="""
您是中国文物知识图谱的Cypher专家，数据库结构如下：

【节点标签】
- Artifact: {{文物名称}}
- Artist: {{姓名（国籍，生卒年）}}
- Material: {{材质名称}}
- Time: {{时期名称（起始年份-结束年份）}}
- Museum: {{博物馆名称}}

【关系类型】
(Artifact)-[:创作者为]->(Artist)
(Artifact)-[:位于]->(Museum)
(Artifact)-[:处于的年代]->(Time)
(Artifact)-[:材质为]->(Material)

【关键约束】
1. 所有属性值都存储在对应节点的name字段
2. 必须使用完整name值精确匹配
3. 返回字段统一用AS result

请忽略问题中的无关信息，专注于文物知识图谱的Cypher查询。
多条件查询请注意逻辑关系，明确查询的对象，使用多行MATCH。
查询朝代相关时，时间节点用模糊匹配,如WHERE t.name STARTS WITH "清朝"
不使用UNION
请生成Cypher查询语句：
回复格式要求：形式为代码块，不要注释。
"""
# 定义Cypher生成模板
cypher_prompt = ChatPromptTemplate(
    [
        ("system", system_prompt),
        MessagesPlaceholder(variable_name="history"),
        ("human", "{input}"),
    ]
)

cypher_chain = cypher_prompt | llm


def execute_cypher(query: str) -> list:
    """执行Cypher查询并返回结果"""
    try:
        result = neo4j_driver.query(query)
        return result
    except Exception as e:
        print(f"数据库查询错误: {str(e)}")
        return []


def refine_cypher(raw_cypher: str) -> str:
    """优化生成的Cypher语句"""
    cypher = re.sub(r"```\w*", "", raw_cypher).strip()

    replacements = [
        (r"刘\(.*?\)", "刘（美国人，1948-2021）"),
        (r"'清朝'", "'清朝（1644-1911）'")
    ]
    for pattern, replacement in replacements:
        cypher = re.sub(pattern, replacement, cypher)

    # 修复 RETURN 中的重复 AS result
    def replace_return_aliases(match):
        fields = match.group(1).split(",")
        new_fields = []
        used_aliases = set()
        for i, field in enumerate(fields):
            prefix = field.strip().split(".")[0]
            alias = f"{prefix.strip()}_result"
            if alias in used_aliases:
                alias = f"{alias}_{i}"
            used_aliases.add(alias)
            new_fields.append(re.sub(r"AS\s+\w+", "", field).strip() + f" AS {alias}")
        return "RETURN " + ", ".join(new_fields)

    cypher = re.sub(r"RETURN\s+(.+)", replace_return_aliases, cypher, flags=re.IGNORECASE)

    # 统一节点别名
    cypher = re.sub(r"(MATCH\s+)(?!a\b)(\w+)", r"\1a", cypher, count=1)

    return cypher



def process_question(question: str,history: BaseChatMessageHistory) -> tuple:
    """处理完整问答流程"""
    # 生成初始Cypher
    with_message_history = RunnableWithMessageHistory(
        cypher_chain,
        lambda config: history,
        input_messages_key="input",
        history_messages_key="history",
    )
    response = with_message_history.invoke(
        {"input": question},
        config={"configurable": {"session_id":"dummy"}},
    )
    raw_cypher = response.content.strip()

    # 优化语句
    final_cypher = refine_cypher(raw_cypher)

    print(f"生成的Cypher语句：\n{final_cypher}")

    # 执行查询
    return final_cypher, execute_cypher(final_cypher)


def format_result(data: list) -> str:
    """美化输出结果"""
    if not data:
        return "未找到相关记录"

    output = []
    for idx, item in enumerate(data, 1):
        item_str = "\n   ".join([f"{k}: {v}" for k, v in item.items()])
        output.append(f"{idx}. {item_str}")

    return "\n\n".join(output)


def get_artifact_answer(question: str,history: BaseChatMessageHistory) -> str:
    """
    处理用户文物知识问题并返回答案

    参数:
        question (str): 用户问题

    返回:
        str: 回答结果
    """
    try:
        # 清理非法Unicode字符
        question = question.encode("utf-8", errors="replace").decode("utf-8")

        # 生成并执行查询
        cypher, result = process_question(question,history)


        # 格式化结果
        answer = format_result(result)

        return answer
    except Exception as e:
        return f"处理问题时出错: {str(e)}"


if __name__ == "__main__":
    test_connection()
    print("""\n文物知识问答系统
输入问题查询文物信息，支持自然语言提问
输入 exit 或 quit 退出系统""")

    # 示例使用封装的函数
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
            # 使用封装函数获取答案
            answer = get_artifact_answer(user_input,history)
            print("\n=== 查询结果 ===")
            print(answer)

        except KeyboardInterrupt:
            print("\n操作已终止")
            break

        except Exception as e:
            print(f"系统错误: {str(e)}")