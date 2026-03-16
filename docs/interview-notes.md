# Interview Notes

## 1. 项目一句话介绍

这是一个面向中文菜谱知识库的工程化 RAG Demo，支持混合检索、多轮对话改写、流式回答和轻量部署展示。

## 2. 为什么不用单一路径检索

我没有只用向量检索，而是用了 Hybrid Search：
- 向量检索负责语义召回
- BM25 负责关键词召回
- 最后用 RRF 做融合重排

这样做的原因是，菜谱类查询里既有语义相似问题，也有非常强的实体词，比如菜名、食材名、做法名。只用单一路径，容易出现：
- 语义相近但目标菜名不准
- 关键词很准但泛化能力弱

相关实现：
- [rag/retriever.py](/d:/PythonProject/recipe-rag-assistant/rag/retriever.py)

## 3. 为什么要做 query contextualization

单轮问答只需要检索当前 query，但真实对话里经常有追问，例如：
- “这个汤还需要鸡蛋吗”
- “那这个要煮多久”
- “继续说这个菜的步骤”

如果直接拿这些问题做检索，召回质量会明显下降。所以我在生成答案前，先做了一步 query contextualization，把省略式问题改写成适合检索的完整问题。

我把这一步设计成“可降级增强”而不是强依赖：
- 能补全最好
- 补全失败就退回原 query

这样不会因为补全超时导致整条链路不可用。

相关实现：
- [rag/generator.py](/d:/PythonProject/recipe-rag-assistant/rag/generator.py)

## 4. 为什么索引复用前要做兼容性校验

很多 RAG Demo 只要本地有 FAISS 索引文件就直接加载，但这并不安全。

原因是向量索引本质上是缓存，不是事实来源。文档内容、文档集合、chunk 数量只要变化，旧索引就可能“能加载但逻辑上已经过期”。

所以这里在复用本地索引前，额外检查：
- 当前 chunk 数量是否一致
- parent_id 集合是否一致
- content_hash 是否一致

不兼容就直接重建索引。

相关实现：
- [rag/vector_store.py](/d:/PythonProject/recipe-rag-assistant/rag/vector_store.py)
- [rag/data_preparation.py](/d:/PythonProject/recipe-rag-assistant/rag/data_preparation.py)

## 5. 为什么缓存检索结果而不缓存最终答案

我只缓存 retrieval 结果，没有缓存最终回答。

原因是检索结果更稳定，边界更清晰：
- 依赖 query、filter、top_k
- 不直接依赖会话历史生成细节
- 适合做 LRU 风格缓存

而最终答案会受这些因素影响：
- 会话上下文
- prompt 细节
- 模型状态
- 输出随机性

直接缓存答案更容易引入错误复用。

相关实现：
- [main.py](/d:/PythonProject/recipe-rag-assistant/main.py)

## 6. 当前怎么评估效果

当前评估分两层：

1. 单元测试  
用于验证工程逻辑是否回归，例如：
- 检索缓存
- rerank 行为
- 索引兼容性判断

相关目录：
- [tests/unit](/d:/PythonProject/recipe-rag-assistant/tests/unit)

2. 轻量离线评估  
用于验证业务效果是否退化，当前覆盖：
- 单轮精确问答
- 多轮上下文追问
- 推荐类问题
- 无答案/应拒答场景

相关文件：
- [eval/run_eval.py](/d:/PythonProject/recipe-rag-assistant/eval/run_eval.py)
- [eval/cases.json](/d:/PythonProject/recipe-rag-assistant/eval/cases.json)

## 7. 当前评估的边界

这套评估适合快速回归，但它不是完整的对话质量评估。

它现在更擅长衡量：
- 是否命中文档
- 是否命中关键词
- 延迟是否变差

它还不能完整衡量：
- 回答是否足够自然
- 是否严格忠于上下文
- 推荐结果是否“更合理”

如果后续继续演进，可以再补：
- 更细的人工标注集
- recommendation 质量标注
- hallucination 检查

## 8. 面试时最值得强调的 4 个点

如果时间有限，我建议重点讲这 4 个点：

1. Hybrid Search 为什么比单一路径更适合菜谱检索
2. Query contextualization 为什么必须做成可降级增强
3. 向量索引为什么不能“能加载就直接复用”
4. 评估为什么不能只看单轮问答，而要覆盖多轮、推荐和拒答
