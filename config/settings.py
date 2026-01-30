"""配置文件管理"""
import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv


class Config:
    """应用配置类"""
    
    def __init__(self):
        # 加载环境变量
        # settings.py位于prompt_optimizer/config/，.env位于prompt_optimizer/根目录
        env_path = Path(__file__).parent.parent / ".env"
        load_dotenv(env_path)
        
        # API密钥配置
        self.deepseek_api_key: Optional[str] = os.getenv("DEEPSEEK_API_KEY")
        self.kimi_api_key: Optional[str] = os.getenv("KIMI_API_KEY")
        self.dashscope_api_key: Optional[str] = os.getenv("DASHSCOPE_API_KEY")
        
        # 模型配置
        self.deepseek_model: str = "deepseek-chat"
        self.deepseek_api_base: str = "https://api.deepseek.com/v1"
        
        self.kimi_model: str = "moonshot-v1-32k"
        self.kimi_api_base: str = "https://api.moonshot.cn/v1"
        
        self.qwen_model: str = "qwen-max"
        self.qwen_api_base: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
        
        # 应用配置
        self.app_name: str = "多AI模型提示词优化工具（支持多轮对话）"
        self.window_size: str = "1200x1000"
        
        # 数据存储配置
        # 数据目录位于prompt_optimizer/data/
        self.data_dir: Path = Path(__file__).parent.parent / "data"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # 日志配置
        # 日志目录位于prompt_optimizer/logs/
        self.log_dir: Path = Path(__file__).parent.parent / "logs"
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.log_file: Path = self.log_dir / "app.log"
        
        # API调用配置
        self.api_timeout: int = 120  # 秒
        self.api_max_retries: int = 3
        self.api_retry_delay: int = 2  # 秒
        
        # UI配置
        self.max_display_length: int = 500  # 对话历史显示的最大长度
        self.summary_threshold: int = 2000  # 需要总结的阈值
        
    def validate_api_keys(self) -> bool:
        """验证API密钥是否都已设置"""
        return all([
            self.deepseek_api_key,
            self.kimi_api_key,
            self.dashscope_api_key
        ])
    
    def get_missing_keys(self) -> list:
        """获取缺失的API密钥列表"""
        missing = []
        if not self.deepseek_api_key:
            missing.append("DEEPSEEK_API_KEY")
        if not self.kimi_api_key:
            missing.append("KIMI_API_KEY")
        if not self.dashscope_api_key:
            missing.append("DASHSCOPE_API_KEY")
        return missing
