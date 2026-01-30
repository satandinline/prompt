"""数据库操作层"""
import mysql.connector
from mysql.connector import Error
from typing import Optional, List, Dict, Tuple
import os
from dotenv import load_dotenv
from contextlib import contextmanager

load_dotenv()


class Database:
    """数据库连接管理"""
    
    def __init__(self):
        self.config = {
            'host': os.getenv('MYSQL_HOST', 'localhost'),
            'port': int(os.getenv('MYSQL_PORT', 3306)),
            'user': os.getenv('MYSQL_USER', 'root'),
            'password': os.getenv('MYSQL_PASSWORD'),
            'database': os.getenv('MYSQL_DATABASE', 'prompt'),
            'charset': 'utf8mb4',
            'collation': 'utf8mb4_unicode_ci'
        }
    
    @contextmanager
    def get_connection(self):
        """获取数据库连接（上下文管理器）"""
        conn = None
        max_retries = 3
        retry_delay = 1
        
        for attempt in range(max_retries):
            try:
                conn = mysql.connector.connect(**self.config)
                yield conn
                conn.commit()
                return
            except Error as e:
                if conn:
                    try:
                        conn.rollback()
                    except:
                        pass
                
                if attempt < max_retries - 1:
                    import time
                    time.sleep(retry_delay)
                    retry_delay *= 2
                else:
                    raise e
            finally:
                if conn and conn.is_connected():
                    conn.close()
    
    def execute_query(self, query: str, params: tuple = None) -> List[Dict]:
        """执行查询并返回结果"""
        with self.get_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(query, params or ())
            results = cursor.fetchall()
            cursor.close()
            return results
    
    def execute_update(self, query: str, params: tuple = None) -> int:
        """执行更新并返回影响的行数"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params or ())
            affected_rows = cursor.rowcount
            cursor.close()
            return affected_rows
    
    def execute_insert(self, query: str, params: tuple = None) -> int:
        """执行插入并返回插入的ID"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params or ())
            last_id = cursor.lastrowid
            cursor.close()
            return last_id


class UserDAO:
    """用户数据访问对象"""
    
    def __init__(self, db: Database):
        self.db = db
    
    def create_user(self, username: str, password_hash: str) -> int:
        """创建用户"""
        query = "INSERT INTO users (username, password_hash) VALUES (%s, %s)"
        return self.db.execute_insert(query, (username, password_hash))
    
    def get_user_by_username(self, username: str) -> Optional[Dict]:
        """通过用户名获取用户"""
        query = "SELECT * FROM users WHERE username = %s"
        results = self.db.execute_query(query, (username,))
        return results[0] if results else None
    
    def get_user_by_id(self, user_id: int) -> Optional[Dict]:
        """通过ID获取用户"""
        query = "SELECT * FROM users WHERE id = %s"
        results = self.db.execute_query(query, (user_id,))
        return results[0] if results else None
    
    def update_last_login(self, user_id: int):
        """更新最后登录时间"""
        query = "UPDATE users SET last_login = NOW() WHERE id = %s"
        self.db.execute_update(query, (user_id,))


class SessionDAO:
    """会话数据访问对象"""
    
    def __init__(self, db: Database):
        self.db = db
    
    def create_session(self, user_id: int, session_name: str = None, 
                      initial_requirement: str = None) -> int:
        """创建会话"""
        query = """
            INSERT INTO sessions (user_id, session_name, initial_requirement) 
            VALUES (%s, %s, %s)
        """
        return self.db.execute_insert(query, (user_id, session_name, initial_requirement))
    
    def get_user_sessions(self, user_id: int) -> List[Dict]:
        """获取用户的所有会话"""
        query = """
            SELECT * FROM sessions 
            WHERE user_id = %s AND is_active = TRUE
            ORDER BY updated_at DESC
        """
        return self.db.execute_query(query, (user_id,))
    
    def get_session(self, session_id: int) -> Optional[Dict]:
        """获取会话详情"""
        query = "SELECT * FROM sessions WHERE id = %s"
        results = self.db.execute_query(query, (session_id,))
        return results[0] if results else None
    
    def update_session(self, session_id: int, session_name: str = None,
                      initial_requirement: str = None):
        """更新会话"""
        if session_name:
            query = "UPDATE sessions SET session_name = %s WHERE id = %s"
            self.db.execute_update(query, (session_name, session_id))
        if initial_requirement is not None:
            query = "UPDATE sessions SET initial_requirement = %s WHERE id = %s"
            self.db.execute_update(query, (initial_requirement, session_id))
    
    def delete_session(self, session_id: int):
        """删除会话（软删除）"""
        query = "UPDATE sessions SET is_active = FALSE WHERE id = %s"
        self.db.execute_update(query, (session_id,))
    
    def update_session_name(self, session_id: int, new_name: str):
        """更新会话名称"""
        query = "UPDATE sessions SET session_name = %s WHERE id = %s"
        self.db.execute_update(query, (new_name, session_id))


class ConversationDAO:
    """对话数据访问对象"""
    
    def __init__(self, db: Database):
        self.db = db
    
    def add_conversation(self, session_id: int, turn_number: int,
                        user_message: str, ai_response: str) -> int:
        """添加对话记录"""
        query = """
            INSERT INTO conversations (session_id, turn_number, user_message, ai_response)
            VALUES (%s, %s, %s, %s)
        """
        return self.db.execute_insert(query, (session_id, turn_number, user_message, ai_response))
    
    def get_session_conversations(self, session_id: int) -> List[Dict]:
        """获取会话的所有对话"""
        query = """
            SELECT * FROM conversations 
            WHERE session_id = %s
            ORDER BY turn_number ASC
        """
        return self.db.execute_query(query, (session_id,))
    
    def delete_conversation(self, conversation_id: int):
        """删除对话记录"""
        query = "DELETE FROM conversations WHERE id = %s"
        self.db.execute_update(query, (conversation_id,))
    
    def clear_session_conversations(self, session_id: int):
        """清空会话的所有对话"""
        query = "DELETE FROM conversations WHERE session_id = %s"
        self.db.execute_update(query, (session_id,))


class OptimizationResultDAO:
    """优化结果数据访问对象"""
    
    def __init__(self, db: Database):
        self.db = db
    
    def save_result(self, session_id: int, original_prompt: str,
                   deepseek_result: str, kimi_result: str, qwen_result: str) -> int:
        """保存优化结果"""
        query = """
            INSERT INTO optimization_results 
            (session_id, original_prompt, deepseek_result, kimi_result, qwen_result)
            VALUES (%s, %s, %s, %s, %s)
        """
        return self.db.execute_insert(query, 
            (session_id, original_prompt, deepseek_result, kimi_result, qwen_result))
    
    def get_session_results(self, session_id: int) -> List[Dict]:
        """获取会话的优化结果"""
        query = """
            SELECT * FROM optimization_results 
            WHERE session_id = %s
            ORDER BY created_at DESC
        """
        return self.db.execute_query(query, (session_id,))
