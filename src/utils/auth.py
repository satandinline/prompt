"""用户认证模块"""
import hashlib
import secrets
from typing import Optional, Dict
from .database import Database, UserDAO


class AuthService:
    """用户认证服务"""
    
    def __init__(self):
        self.db = Database()
        self.user_dao = UserDAO(self.db)
    
    @staticmethod
    def hash_password(password: str) -> str:
        """密码哈希"""
        return hashlib.sha256(password.encode()).hexdigest()
    
    @staticmethod
    def generate_session_token() -> str:
        """生成会话令牌"""
        return secrets.token_hex(32)
    
    def register(self, username: str, password: str) -> Dict:
        """用户注册"""
        if len(username) < 3 or len(username) > 50:
            return {"success": False, "error": "用户名长度必须在3-50个字符之间"}
        
        if len(password) < 6:
            return {"success": False, "error": "密码长度至少6个字符"}
        
        existing_user = self.user_dao.get_user_by_username(username)
        if existing_user:
            return {"success": False, "error": "用户名已存在"}
        
        password_hash = self.hash_password(password)
        
        try:
            user_id = self.user_dao.create_user(username, password_hash)
            return {
                "success": True,
                "user_id": user_id,
                "username": username
            }
        except Exception as e:
            return {"success": False, "error": f"注册失败: {str(e)}"}
    
    def login(self, username: str, password: str) -> Dict:
        """用户登录"""
        user = self.user_dao.get_user_by_username(username)
        
        if not user:
            return {"success": False, "error": "用户名或密码错误"}
        
        password_hash = self.hash_password(password)
        
        if user['password_hash'] != password_hash:
            return {"success": False, "error": "用户名或密码错误"}
        
        self.user_dao.update_last_login(user['id'])
        
        session_token = self.generate_session_token()
        
        return {
            "success": True,
            "user_id": user['id'],
            "username": user['username'],
            "session_token": session_token
        }
    
    def verify_user(self, user_id: int) -> Optional[Dict]:
        """验证用户是否存在"""
        return self.user_dao.get_user_by_id(user_id)
