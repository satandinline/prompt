# 提示词优化工具 (Prompt Optimizer)

一个基于多AI模型协作的提示词优化工具，通过 DeepSeek、Kimi 和 Qwen 三个大模型的逐步优化，帮助用户生成更优质的 AI 提示词。

## ✨ 核心特性

- 🤖 **三模型协作优化**：DeepSeek → Kimi → Qwen 逐步优化提示词
- 👥 **多用户系统**：完整的用户注册、登录、会话管理
- 💬 **对话历史管理**：支持多会话管理，自动生成会话名称
- 🎨 **古风界面设计**：优雅的中文古风主题界面
- 🔒 **安全可靠**：SHA256 密码加密，Session 认证，SQL 注入防护

## 🚀 快速开始

### 环境要求

- Python 3.8+
- MySQL 8.0+

### 安装步骤

1. **克隆项目**
```bash
git clone <repository-url>
cd prompt_optimizer
```

2. **安装依赖**
```bash
pip install -r requirements.txt
```

3. **配置环境变量**

复制 `.env.example` 为 `.env`，并填入你的 API 密钥：
```env
# AI模型API密钥
DEEPSEEK_API_KEY=your_deepseek_api_key
KIMI_API_KEY=your_kimi_api_key
DASHSCOPE_API_KEY=your_qwen_api_key

# MySQL数据库配置
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your_password
MYSQL_DATABASE=prompt
```

4. **初始化数据库**
```bash
python init_db.py
```

5. **启动应用**

```bash
python app.py
```
访问地址：http://localhost:5000

## 📚 技术栈与实现原理

### 后端技术
- **框架**：Flask 2.3+ - 轻量级 Web 框架，负责 API 路由和业务逻辑
- **数据库**：MySQL 8.0 - 关系型数据库，存储用户、会话、对话历史和优化结果
- **AI集成**：LangChain + OpenAI SDK - 统一的 AI 模型调用接口
- **认证**：Flask Session + SHA256 - 基于会话的身份认证，密码使用 SHA256 加密
- **数据库连接**：mysql-connector-python - 原生 MySQL 驱动，支持连接池和事务

### 前端技术
- **纯前端**：HTML5 + CSS3 + JavaScript (ES6+) - 无框架依赖，轻量高效
- **异步通信**：Fetch API - 与后端进行 RESTful API 交互
- **设计风格**：中文古风主题 - 使用传统色彩和书法字体

### AI模型协作机制
- **DeepSeek (deepseek-chat)**：初步分析用户需求，生成结构化提示词框架
- **Kimi (moonshot-v1-128k)**：在 DeepSeek 基础上进行精细化优化，补充细节
- **Qwen (qwen-plus)**：综合前两个模型的结果，生成最终优化版本
- **流程**：用户输入 → 构建上下文 → Step 1 (DeepSeek) → Step 2 (Kimi) → Step 3 (Qwen) → 返回三个结果

### 架构设计
- **三层架构**：表现层（Web界面）→ 业务逻辑层（Flask API）→ 数据访问层（DAO）
- **DAO 模式**：UserDAO、SessionDAO、ConversationDAO、OptimizationResultDAO
- **重试机制**：AI 模型调用失败时自动重试，支持指数退避
- **上下文管理**：自动管理数据库连接的获取、提交和释放

## 📖 功能详解与使用指南

### 1. 用户认证系统

**技术实现：**
- **密码加密**：使用 SHA256 单向哈希算法加密存储密码
- **会话管理**：基于 Flask Session，使用 secrets 模块生成 64 字符的安全令牌
- **认证流程**：登录 → 生成 session_token → 存储在 Flask Session → 后续请求验证

**使用方法：**
1. **注册**：访问登录页，点击"注册"，输入用户名（3-50字符）和密码（≥6字符）
2. **登录**：输入用户名密码，系统验证后自动跳转到主页
3. **登出**：点击右上角"退出登录"按钮，清除会话

**API 接口：**
- `POST /api/auth/register` - 用户注册
- `POST /api/auth/login` - 用户登录
- `POST /api/auth/logout` - 用户登出
- `GET /api/auth/current` - 获取当前用户信息

---

### 2. 会话管理系统

**技术实现：**
- **自动命名**：使用 DeepSeek API 根据初始需求生成 15 字以内的会话名称
- **数据存储**：sessions 表存储会话元数据（用户ID、名称、初始需求、创建时间）
- **软删除机制**：通过 is_active 字段标记删除，不真正删除数据
- **按时间排序**：根据 updated_at 字段降序排列，最新的在最前

**使用方法：**
1. **新建会话**：点击"新建会话"按钮，可选择性输入初始需求
2. **切换会话**：点击左侧会话列表中的任意会话
3. **删除会话**：点击会话右侧的删除按钮（仅标记为不活跃）

**API 接口：**
- `GET /api/sessions` - 获取当前用户的所有会话列表
- `POST /api/sessions` - 创建新会话
- `DELETE /api/sessions/<session_id>` - 删除会话（软删除）

---

### 3. 三模型协作优化

**技术实现：**

**Step 1 - DeepSeek 初步分析：**
- **作用**：分析用户需求，生成结构化的提示词框架
- **实现**：LangChain ChatPromptTemplate + DeepSeek API

**Step 2 - Kimi 精细化优化：**
- **作用**：在 DeepSeek 结果基础上补充细节、优化表达
- **实现**：使用 moonshot-v1-128k 大上下文模型

**Step 3 - Qwen 综合优化：**
- **作用**：综合前两个模型的优点，生成最终版本
- **实现**：使用通义千问 qwen-plus 模型

**重试机制：**
- 每个模型调用失败时自动重试（默认 3 次）
- 指数退避：第 N 次重试等待 N * retry_delay 秒
- 超时设置：单次调用超时 60 秒

**使用方法：**
1. **输入需求**：在左侧"初始需求"输入框填写你的需求描述
2. **开始优化**：点击"开始优化"按钮
3. **查看结果**：等待 10-30 秒，右侧会依次显示三个模型的优化结果
4. **复制结果**：点击每个结果框右上角的"复制"按钮

**API 接口：**
- `POST /api/optimize` - 执行三模型协作优化
  - 请求体：`{"user_text": "需求描述", "conversation_history": [...]}`
  - 返回：`{"success": true, "data": {"deepseek": "...", "kimi": "...", "qwen": "..."}}`

---

### 4. 对话历史管理

**技术实现：**
- **数据模型**：conversations 表（session_id、turn_number、user_message、ai_response）
- **轮次编号**：自动递增的 turn_number 字段，确保对话顺序
- **长文本处理**：AI 回复超过阈值时自动截取首尾 500 字符
- **上下文构建**：格式化为"轮次 N: 用户... AI..."的结构

**使用方法：**
1. **查看历史**：切换会话时自动加载该会话的所有对话
2. **添加对话**：点击"添加对话"按钮，手动输入用户消息和 AI 回复
3. **编辑对话**：点击对话右侧的"编辑"按钮
4. **删除对话**：点击对话右侧的"删除"按钮
5. **清空历史**：点击"清空对话历史"按钮，删除当前会话的所有对话

**上下文传递：**
- 点击"开始优化"时，系统自动将对话历史作为上下文传递给 AI 模型
- 格式：`【对话历史】

轮次1:
用户: ...
AI: ...

轮次2:
...`

**API 接口：**
- `GET /api/conversations/<session_id>` - 获取会话的对话历史
- `POST /api/conversations` - 添加对话记录
- `DELETE /api/conversations/<session_id>` - 清空会话的所有对话

---

### 5. 优化结果存储

**技术实现：**
- **数据模型**：optimization_results 表（session_id、original_prompt、deepseek_result、kimi_result、qwen_result）
- **自动保存**：每次优化完成后自动存储到数据库
- **关联查询**：通过 session_id 关联到具体会话

**API 接口：**
- `POST /api/optimization-results` - 保存优化结果

---

### 6. 文本总结功能

**技术实现：**
- **触发条件**：AI 回复超过 2000 字符时自动触发
- **实现方式**：使用 Qwen 模型进行文本压缩总结
- **简化策略**：取首 500 字符 + 尾 500 字符 + 中间省略说明

**API 接口：**
- `POST /api/summarize` - 对长文本进行总结
  - 请求体：`{"content": "长文本内容"}`
  - 返回：`{"success": true, "summary": "总结结果"}`

## 🏗️ 项目结构

```
prompt_optimizer/
├── config/                 # 配置模块
├── src/                    # 源代码（core/models/utils）
├── static/                 # 前端静态文件
├── markdowns/             # 项目文档
├── app.py                  # Flask主应用
└── init_db.py             # 数据库初始化
```

详细的文件结构和系统架构图请查看 [代码架构图](markdowns/代码架构图.md)。

## 🔧 开发指南

### 数据库架构

项目使用 MySQL 数据库，包含以下四张核心表：

**1. users（用户表）**
```sql
CREATE TABLE users (
    id INT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(64) NOT NULL,  -- SHA256哈希
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP NULL
);
```
- **作用**：存储用户账号信息
- **安全措施**：密码使用 SHA256 单向哈希，不存储明文

**2. sessions（会话表）**
```sql
CREATE TABLE sessions (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    session_name VARCHAR(100),           -- 会话名称（自动生成）
    initial_requirement TEXT,            -- 初始需求
    is_active BOOLEAN DEFAULT TRUE,      -- 软删除标记
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```
- **作用**：管理用户的多个会话
- **命名机制**：使用 DeepSeek API 根据初始需求生成 15 字以内的会话名
- **软删除**：删除时只标记 is_active=FALSE，不删除数据

**3. conversations（对话表）**
```sql
CREATE TABLE conversations (
    id INT PRIMARY KEY AUTO_INCREMENT,
    session_id INT NOT NULL,
    turn_number INT NOT NULL,            -- 对话轮次
    user_message TEXT,                   -- 用户消息
    ai_response TEXT,                    -- AI回复
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES sessions(id)
);
```
- **作用**：存储每个会话的对话历史
- **轮次管理**：turn_number 自动递增，确保对话顺序
- **上下文使用**：优化时作为上下文传递给 AI 模型

**4. optimization_results（优化结果表）**
```sql
CREATE TABLE optimization_results (
    id INT PRIMARY KEY AUTO_INCREMENT,
    session_id INT NOT NULL,
    original_prompt TEXT,                -- 原始输入
    deepseek_result TEXT,                -- DeepSeek结果
    kimi_result TEXT,                    -- Kimi结果
    qwen_result TEXT,                    -- Qwen结果
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES sessions(id)
);
```
- **作用**：存储每次优化的三个模型结果
- **用途**：历史记录查询、结果分析

### API 接口文档

项目共有 **17 个 RESTful API 接口**，分为 5 个模块：

#### 1. 认证接口

**注册**
```http
POST /api/auth/register
Content-Type: application/json

{
  "username": "testuser",
  "password": "password123"
}
```
返回：
```json
{
  "success": true,
  "user_id": 1,
  "username": "testuser"
}
```

**登录**
```http
POST /api/auth/login
Content-Type: application/json

{
  "username": "testuser",
  "password": "password123"
}
```
返回（成功后自动设置 Flask Session）：
```json
{
  "success": true,
  "user_id": 1,
  "username": "testuser",
  "session_token": "abc123..."
}
```

**登出**
```http
POST /api/auth/logout
```

**获取当前用户**
```http
GET /api/auth/current
```

#### 2. 会话接口

**获取会话列表**
```http
GET /api/sessions
```
返回：
```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "session_name": "AI编程助手需求",
      "initial_requirement": "开发一个...",
      "created_at": "2025-01-30T10:00:00",
      "updated_at": "2025-01-30T10:30:00"
    }
  ]
}
```

**创建会话**
```http
POST /api/sessions
Content-Type: application/json

{
  "initial_requirement": "我需要一个能够自动生成代码注释的工具"
}
```
注：session_name 会自动通过 DeepSeek API 生成。

**删除会话**
```http
DELETE /api/sessions/<session_id>
```

#### 3. 对话接口

**获取对话历史**
```http
GET /api/conversations/<session_id>
```

**添加对话记录**
```http
POST /api/conversations
Content-Type: application/json

{
  "session_id": 1,
  "user_message": "用户的问题",
  "ai_response": "AI的回复"
}
```

**清空对话历史**
```http
DELETE /api/conversations/<session_id>
```

#### 4. 优化接口

**执行三模型协作优化**
```http
POST /api/optimize
Content-Type: application/json

{
  "user_text": "我想要一个AI能够理解并执行复杂的编程任务",
  "conversation_history": [
    {
      "user": "之前的问题",
      "ai": "之前的回复"
    }
  ]
}
```
返回：
```json
{
  "success": true,
  "data": {
    "deepseek": "DeepSeek的优化结果...",
    "kimi": "Kimi的优化结果...",
    "qwen": "Qwen的最终优化结果..."
  }
}
```

**总结长文本**
```http
POST /api/summarize
Content-Type: application/json

{
  "content": "超长的文本内容..."
}
```

#### 5. 结果存储接口

**保存优化结果**
```http
POST /api/optimization-results
Content-Type: application/json

{
  "session_id": 1,
  "original_prompt": "原始输入",
  "deepseek_result": "DeepSeek结果",
  "kimi_result": "Kimi结果",
  "qwen_result": "Qwen结果"
}
```

### 核心代码实现

#### DAO 模式实现

项目使用 DAO（Data Access Object）模式封装数据库操作：

```python
# 数据库连接管理（上下文管理器）
class Database:
    @contextmanager
    def get_connection(self):
        conn = mysql.connector.connect(**self.config)
        yield conn
        conn.commit()  # 自动提交
        conn.close()   # 自动关闭

# 用户数据访问
class UserDAO:
    def create_user(self, username, password_hash):
        query = "INSERT INTO users (username, password_hash) VALUES (%s, %s)"
        return self.db.execute_insert(query, (username, password_hash))
```

#### AI 模型调用链

使用 LangChain 构建调用链：

```python
# 1. 创建 Prompt 模板
prompt_template = ChatPromptTemplate.from_messages([
    ("system", "你是一个提示词优化专家..."),
    ("human", "{input}")
])

# 2. 构建调用链（Prompt → Model → Parser）
chain = prompt_template | model | StrOutputParser()

# 3. 执行调用
result = chain.invoke({"input": user_text})
```

#### 重试机制实现

```python
def invoke_with_retry(self, chain, input_data, model_name, max_retries=3):
    for attempt in range(max_retries):
        try:
            return chain.invoke(input_data)
        except Exception as e:
            if attempt < max_retries - 1:
                wait_time = retry_delay * (attempt + 1)  # 指数退避
                time.sleep(wait_time)
            else:
                raise  # 最后一次失败时抛出异常
```

### 本地开发

1. 启动 MySQL 数据库
2. 运行 `python app.py`
3. 访问 http://localhost:5000

## 🤝 贡献指南

欢迎贡献代码！请遵循以下步骤：

1. Fork 本项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

## 📝 开发规范

- 代码风格：遵循 PEP 8
- 命名规范：使用中文描述字段（如 `initial_requirement`）
- 注释规范：关键逻辑添加中文注释
- 提交规范：使用清晰的 commit message

## 🔐 安全说明

- 密码使用 SHA256 加密存储
- API 调用使用 Session 认证
- 所有数据库查询使用参数化，防止 SQL 注入
- 输入验证和长度限制

## 📄 许可证

本项目采用 MIT 许可证。详见 [LICENSE](LICENSE) 文件。

## 👥 团队

本项目由团队协作开发，用于学习和实践 AI 应用开发。

## 📧 联系方式

如有问题或建议，欢迎通过以下方式联系：
- 提交 Issue
- 发送 Pull Request

---

**注意**：使用本工具需要自行申请 DeepSeek、Kimi 和 Qwen 的 API 密钥。
