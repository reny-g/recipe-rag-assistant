"""
使用 sentence_transformers 底层 API 下载模型
显示详细的下载进度
"""
import os
import sys
import time
from pathlib import Path

# 设置镜像和日志
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

print("=" * 70)
print("BAAI/bge-small-zh-v1.5 模型下载工具")
print("=" * 70)
print("\n配置:")
print(f"  镜像源: {os.environ.get('HF_ENDPOINT', '默认')}")
print(f"  缓存目录: {Path.home() / '.cache' / 'huggingface'}")
print("\n开始下载...\n")

try:
    from sentence_transformers import SentenceTransformer
    import huggingface_hub

    # 显示 HuggingFace Hub 版本
    print(f"HuggingFace Hub 版本: {huggingface_hub.__version__}\n")

    start_time = time.time()

    # 使用 SentenceTransformer 直接下载
    # 这个方法会显示下载进度条
    print("正在下载模型文件 (约 92MB)...")
    print("提示: 您会看到每个文件的下载进度条\n")

    model = SentenceTransformer(
        "BAAI/bge-small-zh-v1.5",
        cache_folder=str(Path.home() / ".cache" / "huggingface")
    )

    elapsed = time.time() - start_time

    print(f"\n{'=' * 70}")
    print(f"[OK] 模型下载成功！")
    print(f"     总耗时: {elapsed:.1f} 秒")
    print(f"{'=' * 70}")

    # 测试模型
    print("\n测试模型...")
    test_text = "这是一个测试文本"
    embedding = model.encode(test_text)
    print(f"[OK] 模型工作正常 (向量维度: {len(embedding)})")

    print("\n" + "=" * 70)
    print("现在可以运行主程序了: python main.py")
    print("=" * 70)

except KeyboardInterrupt:
    print("\n\n[INFO] 用户中断下载")
    sys.exit(1)
except Exception as e:
    print(f"\n[FAIL] 下载失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
