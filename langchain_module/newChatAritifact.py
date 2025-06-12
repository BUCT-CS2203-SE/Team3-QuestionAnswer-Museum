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
neo4j_driver = Neo4jGraph(database="artifactsinfo")

def test_connection():
    try:
        result = neo4j_driver.query("RETURN 1 AS result")
        print("Neo4j连接成功") if result else print("Neo4j连接失败")
    except Exception as e:
        print(f"Neo4j连接失败: {str(e)}")

system_prompt = """
您是中国文物知识图谱的Cypher专家，数据库结构如下：

【主节点】
- Artifact: id, Title（标题）

【属性节点及其关系】
- (Artifact)-[:创作者是]->(Artist {name})
- (Artifact)-[:创造年代是]->(Dynasty {name})
- (Artifact)-[:尺寸是]->(Dimension {name})
- (Artifact)-[:材质是]->(Material {name})
- (Artifact)-[:现藏博物馆是]->(Museum {name})
- (Artifact)-[:来源地是]->(PlaceOri {name})
- (Artifact)-[:类型是]->(Classification {name})
- (Artifact)-[:媒介是]->(Medium {name})

【关键约束】
1. 所有 Cypher 查询必须以 Artifact 节点为核心，用别名 `a`
2. 返回字段中必须包含 a.Title AS artifact_name
3. 其他返回字段统一格式：如 Dynasty.name AS dynasty_info，Museum.name AS museum_name 等
4. 使用 WHERE 子句进行匹配（如 WHERE Dynasty.name = "清朝"）
5. 输出格式必须是纯粹的 Cypher 查询语句，使用代码块包裹（```cypher ...```），不能包含自然语言或注释
6. 模型必须生成标准可执行的 Cypher 查询

请根据用户的问题，生成符合以上结构的查询语句：
- 如果用户提问“某朝代有哪些文物”，请模糊匹配朝代节点
- 如果用户提问“某材料有哪些文物”，请匹配材质节点
"""

cypher_prompt = ChatPromptTemplate.from_messages([
    ("system", system_prompt),
    MessagesPlaceholder(variable_name="history"),
    ("human", "{input}"),
])

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
    cypher = re.sub(r"\n\s*\n", "\n", cypher)
    return_match = re.search(r"RETURN\s+(.+)", cypher, re.IGNORECASE)
    if return_match:
        return_fields = return_match.group(1)
        if "artifact_name" not in return_fields:
            new_return_fields = f"a.Title AS artifact_name, {return_fields}"
            cypher = re.sub(r"RETURN\s+.+", f"RETURN {new_return_fields}", cypher)
    else:
        cypher += "\nRETURN a.Title AS artifact_name"
    cypher = re.sub(r"MATCH\s*\(\w+:Artifact", "MATCH (a:Artifact", cypher)
    return cypher

def format_result(data: list) -> str:
    if not data:
        return "未找到相关记录"

    output = []
    for idx, item in enumerate(data, 1):
        artifact_name = item.get("artifact_name", "未知文物")
        if len(item) == 1:
            output.append(f"{idx}. {artifact_name}")
        else:
            descriptions = []
            for key in item:
                if key != "artifact_name":
                    value = item[key]
                    if "dynasty" in key.lower():
                        descriptions.append(f"所处年代：{value}")
                    elif "museum" in key.lower():
                        descriptions.append(f"收藏于：{value}")
                    elif "material" in key.lower():
                        descriptions.append(f"制作材质：{value}")
                    elif "artist" in key.lower():
                        descriptions.append(f"创作者：{value}")
                    elif "classification" in key.lower():
                        descriptions.append(f"类型：{value}")
                    elif "medium" in key.lower():
                        descriptions.append(f"媒介：{value}")
                    elif "dimension" in key.lower():
                        descriptions.append(f"尺寸：{value}")
                    elif "placeori" in key.lower():
                        descriptions.append(f"来源地：{value}")

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
    print("""\n文物知识问答系统\n输入问题查询文物信息，支持自然语言提问\n输入 exit 或 quit 退出系统""")

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
