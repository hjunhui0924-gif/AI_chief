import os
import uuid
import base64
import oss2
import logging
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("oss_utils")

def handle_image_upload(img_bytes: bytes, filename: str, content_type: str) -> str:
    """处理图片上传，如果配置了OSS则上传到OSS，否则回退到Base64编码"""
    oss_access_key = os.getenv("OSS_ACCESS_KEY_ID")
    oss_secret = os.getenv("OSS_ACCESS_KEY_SECRET")
    oss_bucket = os.getenv("OSS_BUCKET")
    oss_endpoint = os.getenv("OSS_ENDPOINT", "oss-cn-beijing.aliyuncs.com")

    if oss_access_key and oss_secret and oss_bucket:
        try:
            auth = oss2.Auth(oss_access_key, oss_secret)
            bucket = oss2.Bucket(auth, oss_endpoint, oss_bucket)

            file_ext = filename.split(".")[-1] if "." in filename else "jpg"
            object_name = f"ai_chief/uploads/{uuid.uuid4().hex}.{file_ext}"
            bucket.put_object(object_name, img_bytes)

            img_url = bucket.sign_url("GET", object_name, 3600, slash_safe=True)
            logger.info(f"图片成功上传至OSS(签名URL): {img_url}")
            return img_url
        except Exception as e:
            logger.error(f"OSS上传失败，触发降级保护，将转为Base64编码传输。错误详情: {e}")
    else:
        logger.warning("未检测到完整的OSS环境变量配置 (缺AccessKey、Secret或Bucket)，直接使用Base64编码传输。")

    logger.info("正在使用Base64处理图片...")
    img_b64 = base64.b64encode(img_bytes).decode("utf-8")
    img_type = content_type or "image/jpeg"
    return f"data:{img_type};base64,{img_b64}"

