from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from langchain_core.messages import HumanMessage

from agent import agent, delete_thread, get_messages
from oss_utils import handle_image_upload

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

app = FastAPI()

STATIC_DIR.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


def clean_model_output(text: str) -> str:
    stripped = text.strip()

    if stripped.startswith("{") and '"recipes"' in stripped:
        return "已根据食材完成搜索，下面直接给你整理推荐结果。"

    blocked_fragments = [
        "Error invoking tool",
        "include_domains",
        "exclude_domains",
        "time_range",
        '"query":',
        '"recipes":',
        '"image_urls":'
    ]
    if any(fragment in text for fragment in blocked_fragments):
        return "搜索过程已省略，下面直接给你整理推荐结果。"

    return text


def extract_display_text(text: str) -> str:
    cleaned = clean_model_output(text)

    blocked_prefixes = [
        "{",
        "搜索关键词：",
        "候选菜谱：",
        "1. 标题：",
        "搜索过程已省略",
        "已根据食材完成搜索"
    ]
    if any(cleaned.lstrip().startswith(prefix) for prefix in blocked_prefixes):
        for marker in [
            "### 基于食材的食谱建议报告",
            "#### 一、当前可用食材",
            "一、当前可用食材"
        ]:
            idx = cleaned.find(marker)
            if idx != -1:
                return cleaned[idx:]
        return ""

    return cleaned


@app.get("/")
def read_root():
    with open(STATIC_DIR / "index.html", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())


@app.get("/history/{thread_id}")
def get_history(thread_id: str):
    """获取指定会话的历史记录"""
    try:
        messages = get_messages(thread_id)
        return {"status": "success", "messages": messages}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.delete("/history/{thread_id}")
def clear_history(thread_id: str):
    """清除指定会话的历史记录"""
    try:
        delete_thread(thread_id)
        return {"status": "success"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.post("/chat")
async def chat(
    message: str = Form(""),
    thread_id: str = Form("default"),
    image: UploadFile = File(None)
):
    try:
        content = []

        if message:
            content.append({"type": "text", "text": message})

        if image and image.filename:
            img_bytes = await image.read()
            img_url = handle_image_upload(img_bytes, image.filename, image.content_type)
            content.append({
                "type": "image_url",
                "image_url": {"url": img_url}
            })

            if not message:
                content.append({
                    "type": "text",
                    "text": "请看看这张图片里的食材能做什么推荐？"
                })

        if not content:
            async def empty_response():
                yield "请输入内容或上传图片。"

            return StreamingResponse(empty_response(), media_type="text/plain; charset=utf-8")

        def stream_generator():
            try:
                user_message = HumanMessage(content=content)
                config = {"configurable": {"thread_id": thread_id}}
                accumulated = ""
                already_sent = ""

                for chunk, _metadata in agent.stream(
                    {"messages": [user_message]},
                    config,
                    stream_mode="messages"
                ):
                    chunk_text = getattr(chunk, "content", "")

                    if isinstance(chunk_text, str):
                        accumulated += chunk_text
                    elif isinstance(chunk_text, list):
                        accumulated += "".join(
                            item.get("text", "")
                            for item in chunk_text
                            if isinstance(item, dict) and item.get("type") == "text"
                        )

                    display_text = extract_display_text(accumulated)
                    if display_text and len(display_text) > len(already_sent):
                        delta = display_text[len(already_sent):]
                        already_sent = display_text
                        yield delta

                if not already_sent:
                    fallback = extract_display_text(accumulated) or "暂时没有生成结果，请再试一次。"
                    yield fallback
            except Exception as e:
                yield f"\n\n**[服务运行错误或网络超时: {str(e)}]**"

        return StreamingResponse(stream_generator(), media_type="text/plain; charset=utf-8")

    except Exception as e:
        async def external_error_response():
            yield f"[初始化异常: {str(e)}]"

        return StreamingResponse(external_error_response(), media_type="text/plain; charset=utf-8")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
