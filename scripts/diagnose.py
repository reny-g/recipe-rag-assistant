"""Quick startup diagnostics for qwen-demo."""

import os
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

if sys.platform == "win32":
    os.system("chcp 65001 > nul")

print("=" * 60)
print("RAG 系统启动诊断")
print("=" * 60)

print("\n[测试 1/5] 导入基础依赖...")
try:
    from dotenv import load_dotenv

    load_dotenv(PROJECT_ROOT / ".env")
    print("  [OK] dotenv 导入成功")
except Exception as exc:
    print(f"  [FAIL] dotenv 导入失败: {exc}")
    sys.exit(1)

print("\n[测试 2/5] 导入 LangChain...")
try:
    from langchain_huggingface import HuggingFaceEmbeddings

    print("  [OK] LangChain / HuggingFace 导入成功")
except Exception as exc:
    print(f"  [FAIL] LangChain 导入失败: {exc}")
    sys.exit(1)

print("\n[测试 3/5] 加载本地嵌入模型...")
print("  (这一步首次运行可能需要几十秒)")
try:
    start_time = time.time()
    embeddings = HuggingFaceEmbeddings(
        model_name="BAAI/bge-small-zh-v1.5",
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )
    print(f"  [OK] 嵌入模型加载成功，耗时 {time.time() - start_time:.1f}s")
except Exception as exc:
    print(f"  [FAIL] 嵌入模型加载失败: {exc}")
    raise

print("\n[测试 4/5] 测试嵌入功能...")
try:
    start_time = time.time()
    result = embeddings.embed_query("测试文本")
    print(f"  [OK] 嵌入功能正常，维度 {len(result)}，耗时 {time.time() - start_time:.2f}s")
except Exception as exc:
    print(f"  [FAIL] 嵌入功能异常: {exc}")
    raise

print("\n[测试 5/5] 初始化 RAG 系统...")
try:
    from main import RagSystem

    start_time = time.time()
    RagSystem()
    print(f"  [OK] RagSystem 初始化成功，耗时 {time.time() - start_time:.1f}s")
except Exception as exc:
    print(f"  [FAIL] RagSystem 初始化失败: {exc}")
    raise

print("\n" + "=" * 60)
print("[OK] 所有诊断步骤通过")
print("=" * 60)
