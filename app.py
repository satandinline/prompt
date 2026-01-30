"""Flask后端API服务器"""
from flask import Flask, request, jsonify, session
from flask_cors import CORS
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from prompt_optimizer.config.settings import Config
from prompt_optimizer.src.utils.logger import Logger
from prompt_optimizer.src.models.ai_models import AIModelManager
from prompt_optimizer.src.core.optimizer import PromptOptimizerCore
from prompt_optimizer.src.utils.auth import AuthService
from prompt_optimizer.src.utils.database import Database, SessionDAO, ConversationDAO, OptimizationResultDAO

app = Flask(__name__, static_folder='static', template_folder='templates')
app.secret_key = 'your-secret-key-change-in-production'
CORS(app, supports_credentials=True)

# 全局变量
config = None
logger = None
model_manager = None
optimizer_core = None
auth_service = None
db = None
session_dao = None
conversation_dao = None
optimization_result_dao = None


def init_app():
    """初始化应用"""
    global config, logger, model_manager, optimizer_core
    global auth_service, db, session_dao, conversation_dao, optimization_result_dao
    
    try:
        # 初始化配置
        config = Config()
        
        # 验证API密钥
        if not config.validate_api_keys():
            missing_keys = config.get_missing_keys()
            raise ValueError(f"缺少API密钥: {', '.join(missing_keys)}")
        
        # 初始化日志
        logger = Logger(config.log_file)
        logger.info("=" * 50)
        logger.info("提示词优化工具Web服务启动")
        logger.info("=" * 50)
        
        # 初始化数据库相关服务
        auth_service = AuthService()
        db = Database()
        session_dao = SessionDAO(db)
        conversation_dao = ConversationDAO(db)
        optimization_result_dao = OptimizationResultDAO(db)
        logger.info("数据库服务初始化成功")
        
        # 初始化AI模型管理器
        model_manager = AIModelManager(config, logger)
        
        # 初始化优化核心
        optimizer_core = PromptOptimizerCore(config, model_manager, logger)
        logger.debug("优化核心初始化成功")
        
        logger.info("✅ 所有服务初始化完成，系统就绪")
        logger.info("=" * 50)
        
    except Exception as e:
        if logger:
            logger.critical(f"初始化失败: {e}", exc_info=True)
        raise


@app.route('/')
def index():
    """返回主页面"""
    from flask import send_from_directory
    import os
    # 检查用户是否登录
    if 'user_id' not in session:
        # 未登录，重定向到登录页
        return send_from_directory(app.static_folder, 'login.html')
    
    index_path = os.path.join(app.static_folder, 'index.html')
    if os.path.exists(index_path):
        return send_from_directory(app.static_folder, 'index.html')
    else:
        return "前端文件未找到，请确保static/index.html存在", 404


@app.route('/login')
def login_page():
    """返回登录页面"""
    from flask import send_from_directory
    return send_from_directory(app.static_folder, 'login.html')


@app.route('/static/<path:filename>')
def static_files(filename):
    """提供静态文件"""
    from flask import send_from_directory
    return send_from_directory(app.static_folder, filename)


@app.route('/api/health', methods=['GET'])
def health():
    """健康检查"""
    return jsonify({
        "status": "ok",
        "message": "服务运行正常"
    })


@app.route('/api/optimize', methods=['POST'])
def optimize():
    """优化提示词"""
    if optimizer_core is None:
        return jsonify({
            "success": False,
            "error": "服务未初始化"
        }), 503
    try:
        data = request.json
        if not data:
            return jsonify({
                "success": False,
                "error": "请求数据为空"
            }), 400
        user_text = data.get('user_text', '').strip()
        conversation_history = data.get('conversation_history', [])
        
        if logger:
            logger.info(f"收到优化请求 - 用户文本长度: {len(user_text)}, 历史对话数: {len(conversation_history)}")
        
        # 验证输入
        if not user_text and not conversation_history:
            return jsonify({
                "success": False,
                "error": "请至少提供初始需求或对话历史"
            }), 400
        
        # 验证输入长度
        if user_text and len(user_text) > 10000:
            return jsonify({
                "success": False,
                "error": "初始需求过长，请控制10000字符以内"
            }), 400
        
        if conversation_history and len(conversation_history) > 50:
            return jsonify({
                "success": False,
                "error": "对话历史过多，请控制50个对话以内"
            }), 400
        
        # 构建输入上下文
        input_context, has_history = optimizer_core.build_input_context(
            user_text,
            conversation_history
        )
        
        # 执行三步优化
        results = {}
        
        # Step 1: DeepSeek
        if logger:
            logger.info("开始Step 1: DeepSeek优化")
        results['deepseek'] = optimizer_core.optimize_step1_deepseek(input_context, has_history)
        if logger:
            logger.debug(f"DeepSeek优化完成，结果长度: {len(results['deepseek'])}")
        
        # Step 2: Kimi
        if logger:
            logger.info("开始Step 2: Kimi优化")
        results['kimi'] = optimizer_core.optimize_step2_kimi(
            input_context, results['deepseek'], has_history
        )
        if logger:
            logger.debug(f"Kimi优化完成，结果长度: {len(results['kimi'])}")
        
        # Step 3: Qwen
        if logger:
            logger.info("开始Step 3: Qwen优化")
        results['qwen'] = optimizer_core.optimize_step3_qwen(
            input_context, results['deepseek'], results['kimi'], has_history
        )
        if logger:
            logger.debug(f"Qwen优化完成，结果长度: {len(results['qwen'])}")
            logger.info("三步优化流程全部完成")
        
        return jsonify({
            "success": True,
            "data": results
        })
        
    except Exception as e:
        if logger:
            logger.error(f"优化失败: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": f"优化失败: {str(e)}"
        }), 500


@app.route('/api/summarize', methods=['POST'])
def summarize():
    """总结长文本"""
    if optimizer_core is None:
        return jsonify({
            "success": False,
            "error": "服务未初始化"
        }), 503
    try:
        data = request.json
        if not data:
            return jsonify({
                "success": False,
                "error": "请求数据为空"
            }), 400
        content = data.get('content', '').strip()
        
        if not content:
            return jsonify({
                "success": False,
                "error": "内容为空"
            }), 400
        
        if len(content) < 500:
            return jsonify({
                "success": False,
                "error": "内容较短，无需总结"
            }), 400
        
        summary = optimizer_core.summarize_text(content)
        
        return jsonify({
            "success": True,
            "data": {
                "original_length": len(content),
                "summary_length": len(summary),
                "summary": summary
            }
        })
        
    except Exception as e:
        if logger:
            logger.error(f"总结失败: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# =========================
# 用户认证API
# =========================

@app.route('/api/auth/register', methods=['POST'])
def register():
    """用户注册"""
    try:
        data = request.json
        username = data.get('username', '').strip()
        password = data.get('password', '').strip()
        
        if logger:
            logger.info(f"用户注册请求 - 用户名: {username}")
        
        if not username or not password:
            return jsonify({
                "success": False,
                "error": "用户名和密码不能为空"
            }), 400
        
        result = auth_service.register(username, password)
        
        if result['success']:
            # 自动为新用户创建默认会话
            session_id = session_dao.create_session(
                result['user_id'], 
                '默认会话',
                None
            )
            if logger:
                logger.info(f"用户注册成功 - 用户ID: {result['user_id']}, 用户名: {username}, 默认会话ID: {session_id}")
            return jsonify(result)
        else:
            if logger:
                logger.warning(f"用户注册失败 - 用户名: {username}, 原因: {result.get('error', 'Unknown')}")
            return jsonify(result), 400
            
    except Exception as e:
        if logger:
            logger.error(f"注册失败: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/auth/login', methods=['POST'])
def login():
    """用户登录"""
    try:
        data = request.json
        username = data.get('username', '').strip()
        password = data.get('password', '').strip()
        
        if logger:
            logger.info(f"用户登录请求 - 用户名: {username}")
        
        if not username or not password:
            return jsonify({
                "success": False,
                "error": "用户名和密码不能为空"
            }), 400
        
        result = auth_service.login(username, password)
        
        if result['success']:
            session['user_id'] = result['user_id']
            session['username'] = result['username']
            if logger:
                logger.info(f"用户登录成功 - 用户ID: {result['user_id']}, 用户名: {username}")
            return jsonify(result)
        else:
            if logger:
                logger.warning(f"用户登录失败 - 用户名: {username}")
            return jsonify(result), 401
            
    except Exception as e:
        if logger:
            logger.error(f"登录失败: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/auth/logout', methods=['POST'])
def logout():
    """用户登出"""
    username = session.get('username', 'Unknown')
    if logger:
        logger.info(f"用户登出 - 用户名: {username}")
    session.clear()
    return jsonify({
        "success": True,
        "message": "登出成功"
    })


@app.route('/api/auth/current', methods=['GET'])
def get_current_user():
    """获取当前用户信息"""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({
            "success": False,
            "error": "未登录"
        }), 401
    
    return jsonify({
        "success": True,
        "user_id": user_id,
        "username": session.get('username')
    })


# =========================
# 会话API
# =========================

@app.route('/api/sessions', methods=['GET'])
def get_sessions():
    """获取用户的所有会话"""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({
            "success": False,
            "error": "未登录"
        }), 401
    
    try:
        if logger:
            logger.debug(f"获取会话列表 - 用户ID: {user_id}")
        sessions = session_dao.get_user_sessions(user_id)
        if logger:
            logger.debug(f"会话列表获取成功 - 数量: {len(sessions)}")
        return jsonify({
            "success": True,
            "data": sessions
        })
    except Exception as e:
        if logger:
            logger.error(f"获取会话列表失败: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/sessions', methods=['POST'])
def create_session_api():
    """创建新会话"""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({
            "success": False,
            "error": "未登录"
        }), 401
    
    try:
        data = request.json
        initial_requirement = data.get('initial_requirement', '')
        
        if logger:
            logger.info(f"创建新会话 - 用户ID: {user_id}, 初始需求长度: {len(initial_requirement)}")
        
        # 如果有初始需求，则生成会话名称；否则使用默认名称
        if initial_requirement and len(initial_requirement.strip()) > 0:
            # 使用DeepSeek生成简短的会话名称
            try:
                summary_prompt = f"""请为以下内容生成一个简短的标题，不超过15个字，只返回标题本身，不要其他内容：

{initial_requirement[:200]}"""
                
                from langchain_core.messages import HumanMessage
                response = model_manager.deepseek_chain.invoke([HumanMessage(content=summary_prompt)])
                session_name = response.content.strip()
                # 限制长度
                if len(session_name) > 15:
                    session_name = session_name[:15]
            except Exception as e:
                if logger:
                    logger.warning(f"生成会话名称失败: {e}")
                session_name = '新会话'
        else:
            session_name = '新会话'
        
        session_id = session_dao.create_session(
            user_id, 
            session_name,
            initial_requirement
        )
        
        if logger:
            logger.info(f"会话创建成功 - 会话ID: {session_id}, 会话名称: {session_name}")
        
        return jsonify({
            "success": True,
            "session_id": session_id,
            "session_name": session_name
        })
    except Exception as e:
        if logger:
            logger.error(f"创建会话失败: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/sessions/<int:session_id>', methods=['DELETE'])
def delete_session_api(session_id):
    """删除会话"""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({
            "success": False,
            "error": "未登录"
        }), 401
    
    try:
        if logger:
            logger.info(f"删除会话 - 用户ID: {user_id}, 会话ID: {session_id}")
        session_dao.delete_session(session_id)
        return jsonify({
            "success": True,
            "message": "会话已删除"
        })
    except Exception as e:
        if logger:
            logger.error(f"删除会话失败: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# =========================
# 对话API
# =========================

@app.route('/api/conversations/<int:session_id>', methods=['GET'])
def get_conversations(session_id):
    """获取会话的所有对话"""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({
            "success": False,
            "error": "未登录"
        }), 401
    
    try:
        if logger:
            logger.debug(f"获取对话列表 - 会话ID: {session_id}")
        conversations = conversation_dao.get_session_conversations(session_id)
        if logger:
            logger.debug(f"对话列表获取成功 - 数量: {len(conversations)}")
        return jsonify({
            "success": True,
            "data": conversations
        })
    except Exception as e:
        if logger:
            logger.error(f"获取对话列表失败: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/conversations', methods=['POST'])
def add_conversation():
    """添加对话记录"""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({
            "success": False,
            "error": "未登录"
        }), 401
    
    try:
        data = request.json
        session_id = data.get('session_id')
        user_message = data.get('user_message', '')
        ai_response = data.get('ai_response', '')
        
        if not session_id or not user_message or not ai_response:
            return jsonify({
                "success": False,
                "error": "缺少必要参数"
            }), 400
        
        # 获取当前轮次号
        existing = conversation_dao.get_session_conversations(session_id)
        turn_number = len(existing) + 1
        
        conversation_id = conversation_dao.add_conversation(
            session_id,
            turn_number,
            user_message,
            ai_response
        )
        
        if logger:
            logger.info(f"添加对话记录 - 会话ID: {session_id}, 轮次: {turn_number}, 对话ID: {conversation_id}")
            logger.debug(f"用户消息长度: {len(user_message)}, AI回复长度: {len(ai_response)}")
        
        # 添加对话后，自动更新会话名称
        try:
            # 获取会话的所有对话
            all_conversations = conversation_dao.get_session_conversations(session_id)
            
            # 构建对话摘要用于生成会话名称
            conversation_summary = ""
            for conv in all_conversations[-3:]:  # 只取最近3轮对话
                conversation_summary += f"用户: {conv['user_message'][:100]}\n"
            
            # 使用DeepSeek生成会话名称
            summary_prompt = f"""请为以下对话生成一个简短的会话标题，不超过15个字，只返回标题本身，不要其他内容：

{conversation_summary}"""
            
            from langchain_core.messages import HumanMessage
            response = model_manager.deepseek_chain.invoke([HumanMessage(content=summary_prompt)])
            new_session_name = response.content.strip()
            # 限制长度
            if len(new_session_name) > 15:
                new_session_name = new_session_name[:15]
            
            # 更新会话名称
            session_dao.update_session_name(session_id, new_session_name)
            
            return jsonify({
                "success": True,
                "conversation_id": conversation_id,
                "new_session_name": new_session_name
            })
        except Exception as e:
            # 即使更新名称失败，对话也已经添加成功
            if logger:
                logger.warning(f"更新会话名称失败: {e}")
            return jsonify({
                "success": True,
                "conversation_id": conversation_id,
                "new_session_name": None
            })
            
    except Exception as e:
        if logger:
            logger.error(f"添加对话失败: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/conversations/<int:session_id>', methods=['DELETE'])
def clear_conversations(session_id):
    """清空会话的所有对话"""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({
            "success": False,
            "error": "未登录"
        }), 401
    
    try:
        if logger:
            logger.info(f"清空对话 - 会话ID: {session_id}")
        conversation_dao.clear_session_conversations(session_id)
        return jsonify({
            "success": True,
            "message": "对话历史已清空"
        })
    except Exception as e:
        if logger:
            logger.error(f"清空对话失败: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# =========================
# 优化结果API
# =========================

@app.route('/api/optimization-results', methods=['POST'])
def save_optimization_result():
    """保存优化结果"""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({
            "success": False,
            "error": "未登录"
        }), 401
    
    try:
        data = request.json
        session_id = data.get('session_id')
        original_prompt = data.get('original_prompt', '')
        deepseek_result = data.get('deepseek_result', '')
        kimi_result = data.get('kimi_result', '')
        qwen_result = data.get('qwen_result', '')
        
        if logger:
            logger.info(f"保存优化结果 - 会话ID: {session_id}")
            logger.debug(f"原始提示词长度: {len(original_prompt)}, DeepSeek: {len(deepseek_result)}, Kimi: {len(kimi_result)}, Qwen: {len(qwen_result)}")
        
        if not session_id:
            return jsonify({
                "success": False,
                "error": "缺少会话 ID"
            }), 400
        
        result_id = optimization_result_dao.save_result(
            session_id,
            original_prompt,
            deepseek_result,
            kimi_result,
            qwen_result
        )
        
        if logger:
            logger.info(f"优化结果保存成功 - 结果ID: {result_id}")
        
        return jsonify({
            "success": True,
            "result_id": result_id
        })
    except Exception as e:
        if logger:
            logger.error(f"保存优化结果失败: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


if __name__ == '__main__':
    import os
    try:
        # 初始化服务（关闯debug模式后不需要reloader检查）
        init_app()
        # 关闯debug模式，避免开发调试信息泄露和性能问题
        app.run(debug=False, host='0.0.0.0', port=5000)
    except Exception as e:
        print(f"启动失败: {e}")
        if logger:
            logger.critical(f"应用启动失败: {e}", exc_info=True)
        sys.exit(1)
