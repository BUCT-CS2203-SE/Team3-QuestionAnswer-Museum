from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
import sys
import os
import logging
from langchain_core.messages import HumanMessage

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 添加langchain_module到系统路径，用于导入智能问答模块
sys.path.append('/tmp/langchain_module')
from chatHistory import ChatHistory
from chatArtifact import get_artifact_answer, test_connection, process_question, neo4j_driver

# 创建聊天服务实例，用于处理智能问答和历史记录
chat_service = ChatHistory()

# 全局变量存储用户名
current_username = None

# Create your views here.

@csrf_exempt
def set_username(request):
    """设置用户名并获取历史记录
    
    请求方式：POST
    请求参数：
        {
            "username": "用户名"  # 必填，用户标识
        }
    返回数据：
        {
            "message": "成功",  # 状态信息
            "history": [...]    # 用户历史会话记录
        }
    错误返回：
        {
            "message": "错误信息",
            "error": "详细错误信息"  # 可选
        }
    """
    global current_username
    if request.method == 'POST':
        try:
            # 解析请求数据
            data = json.loads(request.body.decode('utf-8'))
            username = data.get('username')
            
            # 验证用户名
            if not username:
                return JsonResponse({'message': '用户名不能为空'}, status=400)
                
            # 保存用户名到全局变量
            current_username = username
            logger.debug(f"设置用户名: {current_username}")
                
            # 获取用户历史记录
            logger.debug(f"正在获取用户 {username} 的历史记录")
            raw_history = chat_service.get_all_user_history(username)
            
            # 转换历史记录格式
            formatted_history = []
            for session in raw_history:
                # 获取会话的最后一条用户消息作为summary
                summary = "新会话"
                timestamp = None
                messages = []
                
                # 遍历消息，找到最后一条用户消息作为summary
                for msg in session['messages']:
                    if msg['role'] == 'HUMAN':
                        summary = msg['content']  # 直接更新为最后一条用户消息
                    if not timestamp:
                        timestamp = msg['timestamp']
                    
                    messages.append({
                        "type": "user" if msg['role'] == 'HUMAN' else "bot",
                        "content": msg['content']
                    })
                
                formatted_history.append({
                    "session_id": session.get('session_id', ''),
                    "summary": summary,
                    "timestamp": timestamp.strftime("%Y-%m-%d %H:%M") if timestamp else None,
                    "messages": messages
                })
            
            # 按时间戳降序排序
            formatted_history.sort(key=lambda x: x['timestamp'] if x['timestamp'] else '', reverse=True)
            
            logger.debug(f"转换后的历史记录: {formatted_history}")
            return JsonResponse({'message': '成功', 'history': formatted_history})
        except Exception as e:
            logger.error(f"set_username错误: {str(e)}", exc_info=True)
            return JsonResponse({'message': '服务器错误', 'error': str(e)}, status=500)
    return JsonResponse({'message': '仅支持POST'}, status=405)

@csrf_exempt
def chat(request):
    """处理聊天请求
    
    请求方式：POST
    请求参数：
        {
            "message": "用户消息",      # 必填，用户输入的问题
            "session_id": "会话ID",     # 必填，当前会话的ID
        }
    返回数据：
        {
            "reply": "AI回复内容",  # AI的回复消息
            "knowledge_result": "知识图谱查询结果"  # 知识图谱查询结果
        }
    错误返回：
        {
            "message": "错误信息",
            "error": "详细错误信息"  # 可选
        }
    """
    global current_username
    if request.method == 'POST':
        try:
            # 解析请求数据
            data = json.loads(request.body.decode('utf-8'))
            logger.debug(f"收到聊天请求数据: {data}")
            
            message = data.get('message')
            session_id = data.get('session_id')
            
            # 验证必要参数
            if not current_username:
                logger.error("未找到用户名，请先设置用户名")
                return JsonResponse({'message': '请先设置用户名'}, status=400)
            
            if not message:
                logger.error("消息内容缺失")
                return JsonResponse({'message': '消息内容不能为空'}, status=400)
            
            if not session_id:
                logger.error("会话ID缺失")
                return JsonResponse({'message': '会话ID不能为空'}, status=400)
            
            # 获取历史记录
            logger.debug("获取历史记录")
            history = chat_service._send_session_history(current_username, session_id)
            
            # 从知识图谱获取答案
            logger.debug(f"准备查询知识图谱，问题: {message}")
            try:
                # 使用chatArtifact.py的知识图谱查询功能
                knowledge_result = get_artifact_answer(message, history)
                logger.info("="*50)
                logger.info("知识图谱查询结果:")
                logger.info("-"*30)
                logger.info(knowledge_result)
                logger.info("-"*30)
                logger.info("="*50)
                
                # 使用知识图谱结果生成最终回复
                logger.debug("开始生成最终回复...")
                final_answer = chat_service.stream_response(
                    content=message,
                    systeminput=knowledge_result,  # 传入知识图谱查询结果
                    user_id=current_username,
                    session_id=session_id,
                    language="Chinese"
                )
                
                logger.info("="*50)
                logger.info("AI最终回复:")
                logger.info("-"*30)
                logger.info(final_answer)
                logger.info("-"*30)
                logger.info("="*50)
                
                return JsonResponse({'reply': final_answer})
                
            except Exception as e:
                logger.error(f"知识图谱查询或回复生成错误: {str(e)}", exc_info=True)
                # 如果知识图谱查询失败，尝试直接生成回复
                try:
                    logger.debug("知识图谱查询失败，尝试直接生成回复...")
                    final_answer = chat_service.stream_response(
                        content=message,
                        systeminput="未找到相关记录",  # 表示知识图谱查询失败
                        user_id=current_username,
                        session_id=session_id,
                        language="Chinese"
                    )
                    return JsonResponse({
                        'reply': final_answer,
                        'knowledge_result': "未找到相关记录"  # 添加知识图谱查询结果到返回数据中
                    })
                except Exception as inner_e:
                    logger.error(f"直接生成回复也失败: {str(inner_e)}", exc_info=True)
                    return JsonResponse({
                        'message': '处理消息失败',
                        'error': f"知识图谱查询错误: {str(e)}, 直接回复错误: {str(inner_e)}"
                    }, status=500)
                    
        except json.JSONDecodeError:
            logger.error("JSON解析错误")
            return JsonResponse({'message': '无效的JSON数据'}, status=400)
        except Exception as e:
            logger.error(f"chat错误: {str(e)}", exc_info=True)
            return JsonResponse({'message': '服务器错误', 'error': str(e)}, status=500)
            
    return JsonResponse({'message': '仅支持POST'}, status=405)



#cd /tmp/backend/back
#python manage.py runserver 0.0.0.0:8090