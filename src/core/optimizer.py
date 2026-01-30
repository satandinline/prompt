"""核心优化逻辑"""
from typing import Optional, Dict, Tuple
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from ...config.settings import Config
from .prompt_templates import PromptTemplates
from ..models.ai_models import AIModelManager
from ..utils.logger import Logger


class PromptOptimizerCore:
    """提示词优化核心逻辑"""
    
    def __init__(self, config: Config, model_manager: AIModelManager, logger: Optional[Logger] = None):
        self.config = config
        self.model_manager = model_manager
        self.logger = logger or Logger()
        self.templates = PromptTemplates()
    
    def format_conversation_history(self, conversation_history: list) -> str:
        """格式化对话历史为字符串，对过长的AI回复进行总结"""
        if not conversation_history:
            return ""
        
        formatted = "【对话历史】\n\n"
        formatted += "说明：以下是用户使用优化后的提示词与大模型进行多轮对话的历史记录。\n\n"
        
        for i, turn in enumerate(conversation_history):
            # 验证数据格式
            if not isinstance(turn, dict):
                self.logger.warning(f"跳过无效的对话条目（非字典类型）: {turn}")
                continue
            
            if 'user' not in turn or 'ai' not in turn:
                self.logger.warning(f"跳过无效的对话条目（缺少必要字段）: {turn}")
                continue
            
            formatted += f"轮次 {i+1}:\n"
            formatted += f"用户: {turn['user']}\n"
            
            # 如果AI回复过长，进行总结
            ai_content = turn['ai']
            if not isinstance(ai_content, str):
                ai_content = str(ai_content)
            
            if len(ai_content) > self.config.summary_threshold:
                # 使用简化的总结方法（取前500字符 + 后500字符 + 说明）
                summary = f"{ai_content[:500]}...\n[中间省略约{len(ai_content)-1000}字符]...\n{ai_content[-500:]}"
                formatted += f"AI: {summary}\n"
                formatted += f"(原始回复共{len(ai_content)}字符，已进行摘要处理)\n"
            else:
                formatted += f"AI: {ai_content}\n"
            formatted += "\n"
        
        return formatted
    
    def build_input_context(self, user_text: str, conversation_history: list) -> Tuple[str, bool]:
        """构建输入上下文"""
        # 验证输入
        if not isinstance(conversation_history, list):
            self.logger.warning("conversation_history不是列表类型，转换为空列表")
            conversation_history = []
        
        has_history = len(conversation_history) > 0
        conversation_context = self.format_conversation_history(conversation_history)
        
        # 确保user_text是字符串
        if not isinstance(user_text, str):
            user_text = str(user_text) if user_text else ""
        
        if has_history and user_text:
            input_context = f"初始需求：{user_text}\n\n{conversation_context}"
        elif has_history:
            input_context = f"{conversation_context}"
        else:
            input_context = user_text
        
        return input_context, has_history
    
    def optimize_step1_deepseek(self, input_context: str, has_history: bool) -> str:
        """步骤1: DeepSeek处理"""
        self.logger.info("开始步骤1: DeepSeek处理")
        
        prompts = self.templates.get_deepseek_prompts(has_history)
        prompt_template = ChatPromptTemplate.from_messages([
            ("system", prompts["system"]),
            ("human", prompts["human"])
        ])
        
        chain = prompt_template | self.model_manager.deepseek_model | StrOutputParser()
        result = self.model_manager.invoke_with_retry(
            chain,
            {"input": input_context},
            "DeepSeek"
        )
        
        return result
    
    def optimize_step2_kimi(self, input_context: str, deepseek_output: str, has_history: bool) -> str:
        """步骤2: Kimi完善"""
        self.logger.info("开始步骤2: Kimi完善")
        
        prompts = self.templates.get_kimi_prompts(has_history)
        prompt_template = ChatPromptTemplate.from_messages([
            ("system", prompts["system"]),
            ("human", prompts["human"])
        ])
        
        chain = prompt_template | self.model_manager.kimi_model | StrOutputParser()
        result = self.model_manager.invoke_with_retry(
            chain,
            {
                "input": input_context,
                "deepseek_output": deepseek_output
            },
            "Kimi"
        )
        
        return result
    
    def optimize_step3_qwen(self, input_context: str, deepseek_output: str, kimi_output: str, has_history: bool) -> str:
        """步骤3: Qwen最终完善"""
        self.logger.info("开始步骤3: Qwen最终完善")
        
        prompts = self.templates.get_qwen_prompts(has_history)
        prompt_template = ChatPromptTemplate.from_messages([
            ("system", prompts["system"]),
            ("human", prompts["human"])
        ])
        
        chain = prompt_template | self.model_manager.qwen_model | StrOutputParser()
        result = self.model_manager.invoke_with_retry(
            chain,
            {
                "input": input_context,
                "deepseek_output": deepseek_output,
                "kimi_output": kimi_output
            },
            "Qwen"
        )
        
        return result
    
    def summarize_text(self, content: str) -> str:
        """总结长文本"""
        self.logger.info(f"开始总结文本，长度: {len(content)}字符")
        
        prompt_template = ChatPromptTemplate.from_messages([
            ("system", self.templates.SUMMARY_SYSTEM),
            ("human", self.templates.SUMMARY_HUMAN)
        ])
        
        chain = prompt_template | self.model_manager.qwen_model | StrOutputParser()
        result = self.model_manager.invoke_with_retry(
            chain,
            {"content": content},
            "Qwen (总结)"
        )
        
        self.logger.info(f"总结完成，原长度: {len(content)}字符，现长度: {len(result)}字符")
        return result
