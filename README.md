# AI 私人厨师 🍳

基于 LangChain 与大型语言模型的智能食谱推荐系统。上传食材照片或输入食材清单，AI 自动识别并推荐最合适的菜谱。

![界面预览](static/%E5%88%80%E5%8F%89.png)

## 功能特性

- **📷 食材拍照识别** — 上传食材照片，AI 自动识别可见食材并评估新鲜度
- **🔍 智能食谱搜索** — 基于可用食材，自动调用 Tavily 搜索引擎查找匹配菜谱
- **📊 多维评分排序** — 从营养价值与制作难度两个维度对菜谱量化打分，简单营养的优先推荐
- **📋 结构化报告** — 生成包含食谱信息、评分、推荐理由、参考图片的完整建议报告
- **💬 多会话管理** — 支持多个独立对话，历史会话从后端 SQLite 自动恢复
- **🖼️ 参考图渲染优化** — 支持将模型返回的结构化图片块转换为前端可显示的 Markdown 图片
- **🌊 流式输出优化** — 兼容 AIMessageChunk 与完整 AIMessage，降低结果被误吞的概率
- **📱 响应式设计** — 桌面与移动端均可流畅使用

## 技术栈

| 层级 | 技术 |
|------|------|
| **AI 框架** | LangChain + LangGraph |
| **LLM** | Qwen（DashScope OpenAI 兼容接口） |
| **Web 搜索** | Tavily Search API |
| **后端** | FastAPI（Python） |
| **前端** | Vanilla JS + CSS（响应式） |
| **状态存储** | SQLite（LangGraph Checkpointer） |
| **图片存储** | 阿里云 OSS（签名 URL） |
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

访问 [http://127.0.0.1:8000](http://127.0.0.1:8000) 即可使用。

## 最近优化

### 1. 图片上传与多模态访问

- 上传到 OSS 后不再返回私有直链，而是返回**带时效的签名 URL**，避免模型侧无法下载图片
- 保留 Base64 回退逻辑，便于未配置 OSS 时继续调试

### 2. 历史会话恢复

- 前端启动时通过 `/sessions` 从后端数据库读取全部 thread 列表
- 左侧“最近会话”不再只依赖浏览器本地缓存
- 删除历史会话时会同步删除后端 SQLite 中对应 thread 的记录

### 3. 流式输出稳定性

- 后端流式输出兼容 `AIMessageChunk` 和完整 `AIMessage`
- 避免因只判断 chunk 类型而导致前端落入“暂时没有生成结果”的兜底提示
- 结构化 `image_url` 内容会自动转换成 Markdown 图片，便于前端直接显示

### 4. 前端交互优化

- 历史会话加载完成后直接跳转到底部，不再出现从顶部平滑滚动到底部的过程
- 左侧会话列表支持按最近活跃排序
- 点击空的新会话时不会重复创建新的“新会话”条目
- 仅在新建会话或发送新消息时更新会话顺序，单纯点击历史不会改变排序

### 5. 资源加载与缓存

- 前端脚本增加版本号参数，减少浏览器缓存旧 `main.js` 导致的行为不一致
- 服务默认监听 `127.0.0.1:8000`，避免直接访问 `0.0.0.0` 带来的混淆

## 项目结构

```text
AI_chief/
├── app.py              # FastAPI 服务入口（路由、流式响应）
├── agent.py            # LangChain Agent 定义（工具、系统提示词、检查点）
├── oss_utils.py        # 图片上传工具（OSS 签名 URL / Base64 回退）
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
| GET | `/sessions` | 获取历史会话列表 |
| POST | `/chat` | 发送消息（支持文本+图片） |
| GET | `/history/{thread_id}` | 获取会话历史 |
| DELETE | `/history/{thread_id}` | 删除会话历史 |

## 配置说明

所有配置通过环境变量管理（参见 `.env.example`）：

- **DASHSCOPE_\*** — 通义千问 API 配置（必填）
- **TAVILY_API_KEY** — Tavily 搜索 API 密钥（必填）
- **LANGSMITH_\*** — LangSmith 可观测性配置（可选）
- **OSS_\*** — 阿里云 OSS 图片存储配置（可选）

> 未配置 OSS 时，图片将以 Base64 格式直接嵌入请求中发送给模型；配置 OSS 后，默认返回带有效期的签名 URL。

## 工作原理

```text
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
        │
        ▼
  前端流式渲染文本与参考图
```

## License

[MIT](LICENSE)
