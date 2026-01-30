"""AI模型管理器"""
import time
from typing import Optional
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from ...config.settings import Config
from ..utils.logger import Logger


class AIModelManager:
    """AI模型管理器，负责管理三个AI模型的初始化和调用"""
    
    def __init__(self, config: Config, logger: Optional[Logger] = None):
        self.config = config
        self.logger = logger or Logger()
        
        # 初始化模型
        self.deepseek_model = None
        self.kimi_model = None
        self.qwen_model = None
        self.deepseek_chain = None
        
        self._initialize_models()
    
    def _initialize_models(self):
        """初始化三个AI模型"""
        try:
            # DeepSeek模型
            self.deepseek_model = ChatOpenAI(
                model=self.config.deepseek_model,
                openai_api_key=self.config.deepseek_api_key,
                openai_api_base=self.config.deepseek_api_base,
                timeout=self.config.api_timeout,
                max_retries=self.config.api_max_retries
            )
            self.logger.debug("DeepSeek模型初始化成功")
            
            # Kimi模型
            self.kimi_model = ChatOpenAI(
                model=self.config.kimi_model,
                openai_api_key=self.config.kimi_api_key,
                openai_api_base=self.config.kimi_api_base,
                timeout=self.config.api_timeout,
                max_retries=self.config.api_max_retries
            )
            self.logger.debug("Kimi模型初始化成功")
            
            # Qwen模型
            self.qwen_model = ChatOpenAI(
                model=self.config.qwen_model,
                openai_api_key=self.config.dashscope_api_key,
                openai_api_base=self.config.qwen_api_base,
                timeout=self.config.api_timeout,
                max_retries=self.config.api_max_retries
            )
            self.logger.debug("Qwen模型初始化成功")
            
            # 创建简单的deepseek链用于会话名称生成
            self.deepseek_chain = self.deepseek_model
            self.logger.debug("DeepSeek链初始化成功")
            
            # 所有模型初始化完成后，输出一条总结信息
            self.logger.info("所有AI模型初始化完成 (DeepSeek, Kimi, Qwen)")
            
        except Exception as e:
            self.logger.error(f"模型初始化失败: {e}", exc_info=True)
            raise
    
    def invoke_with_retry(self, chain, input_data: dict, model_name: str, max_retries: int = None) -> str:
        """带重试机制的模型调用"""
        max_retries = max_retries or self.config.api_max_retries
        
        for attempt in range(max_retries):
            try:
                self.logger.debug(f"调用{model_name}模型 (尝试 {attempt + 1}/{max_retries})")
                start_time = time.time()
                
                result = chain.invoke(input_data)
                
                elapsed_time = time.time() - start_time
                self.logger.info(f"{model_name}模型调用成功，耗时 {elapsed_time:.2f}秒")
                
                return result
                
            except Exception as e:
                self.logger.warning(f"{model_name}模型调用失败 (尝试 {attempt + 1}/{max_retries}): {e}")
                
                if attempt < max_retries - 1:
                    wait_time = self.config.api_retry_delay * (attempt + 1)
                    self.logger.debug(f"等待 {wait_time}秒后重试...")
                    time.sleep(wait_time)
                else:
                    self.logger.error(f"{model_name}模型调用最终失败", exc_info=True)
                    raise
