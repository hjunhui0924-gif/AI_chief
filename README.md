# AI 私人厨师 🍳

基于 LangChain 与大型语言模型的智能食谱推荐系统。上传食材照片或输入食材清单，AI 自动识别并推荐最合适的菜谱。

![界面预览](static/%E5%88%80%E5%8F%89.png)

## 功能特性

- **📷 食材拍照识别** — 上传食材照片，AI 自动识别可见食材并评估新鲜度
- **🔍 智能食谱搜索** — 基于可用食材，自动调用 Tavily 搜索引擎查找匹配菜谱
- **📊 多维评分排序** — 从营养价值与制作难度两个维度对菜谱量化打分，简单营养的优先推荐
- **📋 结构化报告** — 生成包含食谱信息、评分、推荐理由、参考图片的完整建议报告
- **💬 多会话管理** — 支持多个独立对话，方便对不同食材组合进行比较
- **📱 响应式设计** — 桌面与移动端均可流畅使用

## 技术栈

| 层级 | 技术 |
|------|------|
| **AI 框架** | LangChain + LangGraph |
| **LLM** | Qwen3.6+（通义千问 DashScope API） |
| **Web 搜索** | Tavily Search API |
| **后端** | FastAPI（Python） |
| **前端** | Vanilla JS + CSS（响应式） |
| **状态存储** | SQLite（LangGraph Checkpointer） |
| **图片存储** | 阿里云 OSS（可选，默认 Base64 内嵌） |
| **链路追踪** | LangSmith（可选） |

## 快速开始

### 前置要求

- Python 3.10+
- 以下 API 密钥（至少需要 DashScope 和 Tavily）：
  - [DashScope (通义千问)](https://help.aliyun.com/zh/model-studio/) — LLM 调用
  - [Tavily](https://tavily.com/) — 食谱搜索
  - [LangSmith](https://smith.langchain.com/)（可选）— 调用链追踪
  - [阿里云 OSS](https://www.aliyun.com/product/oss)（可选）— 图片托管

### 安装

```bash
# 1. 克隆仓库
git clone https://github.com/your-username/ai-chief.git
cd ai-chief

# 2. 安装依赖
pip install -r requirements.txt

# 3. 配置环境变量
cp .env.example .env
# 编辑 .env 填入你的 API 密钥
```

### 运行

```bash
python app.py
```

访问 [http://localhost:8000](http://localhost:8000) 即可使用。

## 项目结构

```
AI_chief/
├── app.py              # FastAPI 服务入口（路由、流式响应）
├── agent.py            # LangChain Agent 定义（工具、系统提示词、检查点）
├── oss_utils.py        # 图片上传工具（OSS 上传 / Base64 回退）
├── requirements.txt    # Python 依赖
├── .env.example        # 环境变量模板
├── .gitignore
├── resources/
│   └── personal_chief.db   # SQLite 会话存储（自动生成）
├── static/
│   ├── index.html      # 前端页面
│   ├── main.js         # 前端交互逻辑
│   ├── style.css       # 前端样式
│   └── 刀叉.png        # 应用图标
└── init_model.ipynb    # 模型初始化实验 Notebook
```

## API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/` | 返回主页面 |
| POST | `/chat` | 发送消息（支持文本+图片） |
| GET | `/history/{thread_id}` | 获取会话历史 |
| DELETE | `/history/{thread_id}` | 删除会话历史 |

## 配置说明

所有配置通过环境变量管理（参见 `.env.example`）：

- **DASHSCOPE\_\*** — 通义千问 API 配置（必填）
- **TAVILY\_API_KEY** — Tavily 搜索 API 密钥（必填）
- **LANGSMITH\_\*** — LangSmith 可观测性配置（可选）
- **OSS\_\*** — 阿里云 OSS 图片存储配置（可选）

> 未配置 OSS 时，图片将以 Base64 格式直接嵌入请求中发送给模型。

## 工作原理

```
用户上传食材图片/输入食材清单
        │
        ▼
   AI 识别食材并评估新鲜度
        │
        ▼
   调用 Tavily 搜索匹配菜谱
        │
        ▼
   从营养与难度维度排序
        │
        ▼
   生成结构化建议报告
```

## License

[MIT](LICENSE)
