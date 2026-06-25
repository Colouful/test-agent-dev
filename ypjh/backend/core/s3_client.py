from __future__ import annotations

import os
import uuid

MOCK_BEDROCK: bool = os.getenv("MOCK_BEDROCK", "true").lower() == "true"

# S3 桶名：优先从环境变量读取，回退到账号级默认桶
_DEFAULT_BUCKET = "wrongbook-images-851725516537"
S3_BUCKET: str = os.getenv("S3_BUCKET", _DEFAULT_BUCKET)


def _s3_client():  # type: ignore[no-untyped-def]
    import boto3  # type: ignore[import-untyped]
    return boto3.client("s3", region_name=os.getenv("AWS_DEFAULT_REGION", "us-east-1"))


def upload_image(data: bytes, user_id: str, ext: str) -> str:
    """上传图片到 S3，返回 key（格式 R20）。MOCK 时返回假 key。"""
    key = f"{user_id}/original/{uuid.uuid4()}.{ext}"
    if MOCK_BEDROCK:
        return key
    _s3_client().put_object(Bucket=S3_BUCKET, Key=key, Body=data)
    return key


def get_image_bytes(key: str) -> bytes:
    """从 S3 下载图片字节。"""
    resp = _s3_client().get_object(Bucket=S3_BUCKET, Key=key)
    return resp["Body"].read()


def generate_presigned_url(key: str, expires: int = 3600) -> str:
    """生成预签名 URL（R23）。MOCK 时返回 https://mock-s3/key。"""
    if MOCK_BEDROCK:
        return f"https://mock-s3.example.com/{key}"
    return _s3_client().generate_presigned_url(
        "get_object",
        Params={"Bucket": S3_BUCKET, "Key": key},
        ExpiresIn=expires,
    )
