import os
import sqlite3
from pathlib import Path

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from langchain.messages import AIMessage, HumanMessage
from langchain_core.tools import tool
from langchain_tavily import TavilySearch
from langgraph.checkpoint.sqlite import SqliteSaver

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "resources" / "personal_chief.db"

model = init_chat_model(
    model="qwen3.5-flash",
    model_provider="openai",
    base_url=os.getenv("DASHSCOPE_BASE_URL"),
    api_key=os.getenv("DASHSCOPE_API_KEY")
)

raw_web_search = TavilySearch(
    max_results=5,
    topic="general",
    include_images=True,
    include_answer=False,
    include_raw_content=False,
    search_depth="basic",
    handle_tool_error=True,
    handle_validation_error="搜索参数格式错误，请改用更短的中文菜谱关键词重新搜索。"
)


@tool
def search_recipes(query: str) -> str:
    """搜索食谱信息。只传入简短中文查询词，不要传其它参数。"""
    try:
        result = raw_web_search.invoke({"query": query})
    except Exception as e:
        return f"搜索失败：{str(e)}"

    recipe_lines = []
    for index, item in enumerate(result.get("results", [])[:5], start=1):
        title = item.get("title", "").strip() or "未命名菜谱"
        url = item.get("url", "").strip()
        summary = (item.get("content", "") or "").strip().replace("\n", " ")
        recipe_lines.append(
            f"{index}. 标题：{title}\n"
            f"   摘要：{summary}\n"
            f"   链接：{url}"
        )

    image_lines = []
    for index, image_url in enumerate(result.get("images", [])[:5], start=1):
        if isinstance(image_url, str) and image_url.startswith("http"):
            image_lines.append(f"{index}. {image_url}")

    if not recipe_lines:
        recipe_lines.append("没有搜到特别合适的公开菜谱结果，请结合常识给出推荐。")

    text_parts = [
        f"搜索关键词：{query}",
        "",
        "候选菜谱：",
        "\n".join(recipe_lines)
    ]

    if image_lines:
        text_parts.extend(["", "可用参考图片：", "\n".join(image_lines)])

    return "\n".join(text_parts)


connection = sqlite3.connect(DB_PATH, check_same_thread=False)
checkpoint = SqliteSaver(connection)
checkpoint.setup()

system_prompt = """
你是一名私人厨师。收到用户提供的食材照片或清单后，请按以下流程操作：

1.识别和评估食材：若用户提供照片，首先辨识所有可见食材。基于食材的外观状态，评估其新鲜度与可用量，整理出一份 “当前可用食材清单”。
2.智能食谱检索：优先调用 web_search 工具，以 “可用食材清单” 为核心关键词，查找可行菜谱。
3.多维度评估与排序：从营养价值和制作难度两个维度对检索到的候选食谱进行量化打分，并根据得分排序，制作简单且营养丰富的排名靠前。
4.结构化方案输出：把排序后的食谱整理为一份结构清晰的建议报告，要包含食谱信息、得分、推荐理由、食谱的参考图片，帮助用户快速做出决策。

请严格按照流程，优先调用 web_search 工具搜索食谱，搜索不到的情况下才能自己发挥。
"""

agent = create_agent(
    model=model,
    tools=[search_recipes],
    system_prompt=system_prompt,
    checkpointer=checkpoint
)


def get_messages(thread_id: str) -> list[dict[str, str]]:
    cp = checkpoint.get({"configurable": {"thread_id": thread_id}})
    if not cp:
        return []

    channel_values = cp.get("channel_values")
    if not channel_values:
        return []

    messages = channel_values.get("messages", [])
    if not messages:
        return []

    result = []
    for msg in messages:
        if not msg.content:
            continue

        if isinstance(msg, HumanMessage):
            content = msg.content
            if isinstance(content, list):
                text_content = next(
                    (item["text"] for item in content if item.get("type") == "text"),
                    "[图片请求]"
                )
                image_url = None
                for item in content:
                    if item.get("type") == "image_url":
                        image_payload = item.get("image_url", {})
                        if isinstance(image_payload, dict):
                            candidate = image_payload.get("url")
                            if isinstance(candidate, str) and candidate.startswith("http"):
                                image_url = candidate
                                break

                message = {"role": "user", "content": text_content}
                if image_url:
                    message["image_url"] = image_url
                result.append(message)
            else:
                result.append({"role": "user", "content": content})
        elif isinstance(msg, AIMessage):
            result.append({"role": "assistant", "content": msg.content})

    return result


def derive_session_title(messages: list[dict[str, str]]) -> str:
    for message in messages:
        if message.get("role") != "user":
            continue

        content = str(message.get("content", "")).replace("\n", " ").strip()
        if content and content != "[图片请求]":
            return content[:12]
        if message.get("image_url"):
            return "图片识别"

    return "新会话"


def list_threads() -> list[dict[str, str]]:
    rows = connection.execute(
        """
        SELECT thread_id, MAX(sort_rowid) AS latest_rowid
        FROM (
            SELECT thread_id, rowid AS sort_rowid FROM checkpoints
            UNION ALL
            SELECT thread_id, rowid AS sort_rowid FROM writes
        )
        GROUP BY thread_id
        ORDER BY latest_rowid DESC
        """
    ).fetchall()

    result = []
    for (thread_id, _latest_rowid) in rows:
        try:
            messages = get_messages(thread_id)
        except Exception:
            messages = []

        title = derive_session_title(messages) if messages else thread_id
        result.append({
            "thread_id": thread_id,
            "title": title
        })

    return result


def delete_thread(thread_id: str):
    checkpoint.delete_thread(thread_id)
