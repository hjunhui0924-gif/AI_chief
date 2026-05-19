from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from langchain.messages import AIMessage, AIMessageChunk, HumanMessage

from agent import agent, delete_thread, get_messages, list_threads
from oss_utils import handle_image_upload

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

app = FastAPI()

STATIC_DIR.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


def extract_renderable_content(content) -> str:
    if isinstance(content, str):
        return content

    if not isinstance(content, list):
        return ""

    parts = []
    for item in content:
        if not isinstance(item, dict):
            continue

        item_type = item.get("type")
        if item_type == "text":
            text = item.get("text", "")
            if text:
                parts.append(text)
            continue

        if item_type == "image_url":
            image_payload = item.get("image_url", {})
            if isinstance(image_payload, dict):
                image_url = image_payload.get("url", "")
                if image_url:
                    parts.append(f"\n\n![参考图]({image_url})\n")

    return "".join(parts)


@app.get("/")
def read_root():
    with open(STATIC_DIR / "index.html", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())


@app.get("/sessions")
def get_sessions():
    try:
        return {"status": "success", "sessions": list_threads()}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.get("/history/{thread_id}")
def get_history(thread_id: str):
    try:
        messages = get_messages(thread_id)
        return {"status": "success", "messages": messages}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.delete("/history/{thread_id}")
def clear_history(thread_id: str):
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
                has_output = False
                seen_text = ""

                for chunk, _metadata in agent.stream(
                    {"messages": [user_message]},
                    config,
                    stream_mode="messages"
                ):
                    if not isinstance(chunk, (AIMessageChunk, AIMessage)):
                        continue

                    text = extract_renderable_content(chunk.content)
                    if not text:
                        continue

                    if isinstance(chunk, AIMessageChunk):
                        has_output = True
                        seen_text += text
                        yield text
                        continue

                    if not text.startswith(seen_text):
                        has_output = True
                        seen_text = text
                        yield text
                        continue

                    delta = text[len(seen_text):]
                    if delta:
                        has_output = True
                        seen_text = text
                        yield delta

                if not has_output:
                    yield "暂时没有生成结果，请再试一次。"
            except Exception as e:
                yield f"\n\n**[服务运行错误或网络超时: {str(e)}]**"

        return StreamingResponse(stream_generator(), media_type="text/plain; charset=utf-8")

    except Exception as e:
        async def external_error_response():
            yield f"[初始化异常: {str(e)}]"

        return StreamingResponse(external_error_response(), media_type="text/plain; charset=utf-8")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
