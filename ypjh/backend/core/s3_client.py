from __future__ import annotations

import os
import uuid

MOCK_BEDROCK: bool = os.getenv("MOCK_BEDROCK", "true").lower() == "true"


def upload_image(data: bytes, user_id: str, ext: str) -> str:
    """上传图片到 S3，返回 key（格式 R20）。MOCK 时返回假 key。"""
    key = f"{user_id}/original/{uuid.uuid4()}.{ext}"
    if MOCK_BEDROCK:
        return key
    import boto3  # type: ignore[import-untyped]
    bucket = os.environ["S3_BUCKET"]
    boto3.client("s3").put_object(Bucket=bucket, Key=key, Body=data)
    return key


def generate_presigned_url(key: str, expires: int = 3600) -> str:
    """生成预签名 URL（R23）。MOCK 时返回 https://mock-s3/key。"""
    if MOCK_BEDROCK:
        return f"https://mock-s3.example.com/{key}"
    import boto3  # type: ignore[import-untyped]
    bucket = os.environ["S3_BUCKET"]
    return boto3.client("s3").generate_presigned_url(
        "get_object",
        Params={"Bucket": bucket, "Key": key},
        ExpiresIn=expires,
    )
