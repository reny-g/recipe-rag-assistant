import argparse
import json
import logging
import statistics
import sys
import time
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from config import load_project_env
from main import RagSystem


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

DEFAULT_CASES_PATH = Path(__file__).with_name("cases.json")
DEFAULT_OUTPUT_PATH = Path(__file__).with_name("results.json")
DEFAULT_REPORT_PATH = Path(__file__).with_name("report.md")
DEFAULT_REFUSAL_KEYWORDS = [
    "没有找到",
    "没有相关",
    "信息不足",
    "无法根据",
    "抱歉",
]

METRIC_DESCRIPTIONS = {
    "total_cases": "评估样例总数",
    "doc_target_case_count": "具备明确目标文档的样例数量",
    "no_answer_case_count": "无答案/应拒答样例数量",
    "retrieval_top1_accuracy": "目标文档样例中，Top1 命中目标文档的比例",
    "retrieval_hit_any_rate": "目标文档样例中，返回结果任意位置命中目标文档的比例",
    "avg_retrieval_latency_ms": "平均检索耗时（毫秒）",
    "median_retrieval_latency_ms": "检索耗时中位数（毫秒）",
    "p95_retrieval_latency_ms": "检索耗时 P95（毫秒）",
    "retrieval_fail_count": "目标文档样例中，Top1 未命中的样例数",
    "avg_answer_latency_ms": "平均回答耗时（毫秒）",
    "median_answer_latency_ms": "回答耗时中位数（毫秒）",
    "p95_answer_latency_ms": "回答耗时 P95（毫秒）",
    "answer_keyword_hit_all_rate": "需要关键词命中的样例中，答案全命中的比例",
    "answer_keyword_hit_any_rate": "需要关键词命中的样例中，答案任意命中的比例",
    "no_answer_refusal_rate": "无答案样例中，答案表现出拒答/信息不足的比例",
}

METRIC_LABELS_ZH = {
    "total_cases": "样例总数",
    "doc_target_case_count": "目标文档样例数",
    "no_answer_case_count": "无答案样例数",
    "retrieval_top1_accuracy": "检索 Top1 准确率",
    "retrieval_hit_any_rate": "检索命中率",
    "avg_retrieval_latency_ms": "平均检索耗时(ms)",
    "median_retrieval_latency_ms": "检索耗时中位数(ms)",
    "p95_retrieval_latency_ms": "检索耗时 P95(ms)",
    "retrieval_fail_count": "检索失败样例数",
    "avg_answer_latency_ms": "平均回答耗时(ms)",
    "median_answer_latency_ms": "回答耗时中位数(ms)",
    "p95_answer_latency_ms": "回答耗时 P95(ms)",
    "answer_keyword_hit_all_rate": "答案关键词全命中率",
    "answer_keyword_hit_any_rate": "答案关键词任意命中率",
    "no_answer_refusal_rate": "无答案拒答率",
}


def load_cases(cases_path: Path) -> list[dict[str, Any]]:
    data = json.loads(cases_path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("Evaluation cases must be a JSON array.")
    return data


def _normalize_history(case: dict[str, Any]) -> list[dict[str, str]]:
    history = []
    for item in case.get("history", []):
        role = str(item.get("role", "")).strip()
        content = str(item.get("content", "")).strip()
        if role and content:
            history.append({"role": role, "content": content})
    return history


def _target_docs(case: dict[str, Any]) -> list[str]:
    docs = []
    expected_doc = str(case.get("expected_doc", "")).strip()
    if expected_doc:
        docs.append(expected_doc)
    docs.extend(str(item).strip() for item in case.get("expected_docs", []) if str(item).strip())
    return docs


def run_case(system: RagSystem, case: dict[str, Any], with_answer: bool) -> dict[str, Any]:
    query = str(case["query"]).strip()
    history = _normalize_history(case)
    target_docs = _target_docs(case)
    target_doc_set = set(target_docs)
    expected_keywords = [str(item).strip() for item in case.get("expected_keywords", []) if str(item).strip()]
    expect_no_answer = bool(case.get("expect_no_answer", False))
    refusal_keywords = [
        str(item).strip()
        for item in case.get("refusal_keywords", DEFAULT_REFUSAL_KEYWORDS)
        if str(item).strip()
    ]

    retrieval_started_at = time.perf_counter()
    contextualized_query = system.generation_module.contextualize_query(query, history)
    filters = system._extract_filters_from_query(contextualized_query)
    relevant_chunks = system._retrieve_chunks(contextualized_query, filters)
    relevant_docs = system.data_module.get_parent_documents(relevant_chunks)
    retrieval_latency_ms = (time.perf_counter() - retrieval_started_at) * 1000

    retrieved_doc_names = [doc.metadata.get("dish_name", "") for doc in relevant_docs]
    top_doc = retrieved_doc_names[0] if retrieved_doc_names else ""

    result: dict[str, Any] = {
        "id": case["id"],
        "query": query,
        "history": history,
        "contextualized_query": contextualized_query,
        "expected_docs": target_docs,
        "expect_no_answer": expect_no_answer,
        "top_doc": top_doc,
        "retrieved_docs": retrieved_doc_names,
        "retrieval_hit_top1": (top_doc in target_doc_set) if target_doc_set else None,
        "retrieval_hit_any": bool(target_doc_set.intersection(retrieved_doc_names)) if target_doc_set else None,
        "retrieval_latency_ms": round(retrieval_latency_ms, 2),
    }

    if with_answer:
        answer_started_at = time.perf_counter()
        answer = system.generation_module.generate_answer(
            query,
            relevant_docs,
            history,
            stream=False,
        )
        answer_latency_ms = (time.perf_counter() - answer_started_at) * 1000
        answer_text = answer if isinstance(answer, str) else "".join(answer)

        result["answer"] = answer_text
        result["answer_latency_ms"] = round(answer_latency_ms, 2)
        result["answer_keyword_hit_all"] = (
            all(keyword in answer_text for keyword in expected_keywords) if expected_keywords else None
        )
        result["answer_keyword_hit_any"] = (
            any(keyword in answer_text for keyword in expected_keywords) if expected_keywords else None
        )
        result["no_answer_refusal_hit"] = (
            any(keyword in answer_text for keyword in refusal_keywords) if expect_no_answer else None
        )

    return result


def summarize(results: list[dict[str, Any]], with_answer: bool) -> dict[str, Any]:
    retrieval_latencies = [item["retrieval_latency_ms"] for item in results]
    doc_target_results = [item for item in results if item.get("expected_docs")]
    no_answer_results = [item for item in results if item.get("expect_no_answer")]

    summary: dict[str, Any] = {
        "total_cases": len(results),
        "doc_target_case_count": len(doc_target_results),
        "no_answer_case_count": len(no_answer_results),
        "retrieval_top1_accuracy": round(
            sum(1 for item in doc_target_results if item["retrieval_hit_top1"]) / max(len(doc_target_results), 1),
            4,
        ),
        "retrieval_hit_any_rate": round(
            sum(1 for item in doc_target_results if item["retrieval_hit_any"]) / max(len(doc_target_results), 1),
            4,
        ),
        "avg_retrieval_latency_ms": round(statistics.mean(retrieval_latencies), 2) if retrieval_latencies else 0.0,
        "median_retrieval_latency_ms": round(statistics.median(retrieval_latencies), 2) if retrieval_latencies else 0.0,
        "p95_retrieval_latency_ms": round(_percentile(retrieval_latencies, 0.95), 2) if retrieval_latencies else 0.0,
        "retrieval_fail_count": sum(1 for item in doc_target_results if not item["retrieval_hit_top1"]),
    }

    if with_answer:
        answer_latencies = [item["answer_latency_ms"] for item in results]
        keyword_results = [item for item in results if item.get("answer_keyword_hit_all") is not None]
        refusal_results = [item for item in no_answer_results if item.get("no_answer_refusal_hit") is not None]

        summary["avg_answer_latency_ms"] = round(statistics.mean(answer_latencies), 2) if answer_latencies else 0.0
        summary["median_answer_latency_ms"] = round(statistics.median(answer_latencies), 2) if answer_latencies else 0.0
        summary["p95_answer_latency_ms"] = round(_percentile(answer_latencies, 0.95), 2) if answer_latencies else 0.0
        summary["answer_keyword_hit_all_rate"] = round(
            sum(1 for item in keyword_results if item["answer_keyword_hit_all"]) / max(len(keyword_results), 1),
            4,
        )
        summary["answer_keyword_hit_any_rate"] = round(
            sum(1 for item in keyword_results if item["answer_keyword_hit_any"]) / max(len(keyword_results), 1),
            4,
        )
        summary["no_answer_refusal_rate"] = round(
            sum(1 for item in refusal_results if item["no_answer_refusal_hit"]) / max(len(refusal_results), 1),
            4,
        )

    return summary


def build_human_readable_summary(summary: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "metric": key,
            "value": value,
            "label_zh": _metric_label_zh(key),
            "description_zh": METRIC_DESCRIPTIONS.get(key, ""),
        }
        for key, value in summary.items()
    ]


def build_failure_examples(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    failures = []
    for item in results:
        if item.get("retrieval_hit_top1") is None or item["retrieval_hit_top1"]:
            continue
        failures.append(
            {
                "id": item["id"],
                "history": item.get("history", []),
                "query": item["query"],
                "expected_docs": item.get("expected_docs", []),
                "top_doc": item["top_doc"],
                "retrieved_docs": item["retrieved_docs"],
                "reason_zh": "目标文档没有排在第 1 位",
            }
        )
    return failures


def build_markdown_report(summary: dict[str, Any], results: list[dict[str, Any]], failures: list[dict[str, Any]]) -> str:
    lines = [
        "# Recipe RAG Assistant 评估报告",
        "",
        "## 指标概览",
        "",
        "| 指标 | 数值 | 中文说明 |",
        "| --- | ---: | --- |",
    ]
    for key, value in summary.items():
        lines.append(f"| {_metric_label_zh(key)} | {value} | {METRIC_DESCRIPTIONS.get(key, '')} |")

    lines.extend(["", "## 失败样例", ""])
    if not failures:
        lines.append("当前样例集中，所有目标文档样例都命中了 Top1。")
    else:
        lines.append("| ID | 历史轮次 | 问题 | 期望文档 | 实际 Top1 | 说明 |")
        lines.append("| --- | ---: | --- | --- | --- | --- |")
        for item in failures:
            lines.append(
                f"| {item['id']} | {len(item.get('history', []))} | {item['query']} | "
                f"{' / '.join(item['expected_docs'])} | {item['top_doc']} | {item['reason_zh']} |"
            )

    lines.extend(
        [
            "",
            "## 样例明细",
            "",
            "| ID | 类别 | 历史轮次 | 问题 | 改写后查询 | 期望文档 | 实际 Top1 | Top1命中 | 任意命中 | 检索耗时(ms) |",
            "| --- | --- | ---: | --- | --- | --- | --- | --- | --- | ---: |",
        ]
    )
    for item in results:
        case_kind = "无答案" if item.get("expect_no_answer") else ("目标文档" if item.get("expected_docs") else "其他")
        lines.append(
            f"| {item['id']} | {case_kind} | {len(item.get('history', []))} | {item['query']} | "
            f"{item['contextualized_query']} | {' / '.join(item.get('expected_docs', []))} | {item['top_doc']} | "
            f"{_hit_text(item.get('retrieval_hit_top1'))} | {_hit_text(item.get('retrieval_hit_any'))} | {item['retrieval_latency_ms']} |"
        )

    return "\n".join(lines) + "\n"


def print_summary(summary: dict[str, Any]) -> None:
    print("\n评估结果概览")
    print("============")
    for key, value in summary.items():
        print(f"{_metric_label_zh(key)}: {value}")
        description = METRIC_DESCRIPTIONS.get(key)
        if description:
            print(f"  说明: {description}")


def _percentile(values: list[float], ratio: float) -> float:
    ordered = sorted(values)
    if not ordered:
        return 0.0
    index = max(0, min(len(ordered) - 1, int(round((len(ordered) - 1) * ratio))))
    return ordered[index]


def _metric_label_zh(key: str) -> str:
    return METRIC_LABELS_ZH.get(key, key)


def _hit_text(value: bool | None) -> str:
    if value is None:
        return "-"
    return "是" if value else "否"


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a lightweight evaluation for Recipe RAG Assistant.")
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES_PATH, help="Path to eval cases JSON.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH, help="Where to write eval results JSON.")
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT_PATH, help="Where to write Markdown report.")
    parser.add_argument(
        "--with-answer",
        action="store_true",
        help="Also call the answer-generation model and record answer latency / keyword hits.",
    )
    args = parser.parse_args()

    load_project_env()
    cases = load_cases(args.cases)

    system = RagSystem()
    system.build_knowledge_base()

    results = [run_case(system, case, with_answer=args.with_answer) for case in cases]
    summary = summarize(results, with_answer=args.with_answer)
    summary_readable = build_human_readable_summary(summary)
    failure_examples = build_failure_examples(results)
    markdown_report = build_markdown_report(summary, results, failure_examples)

    payload = {
        "summary": summary,
        "summary_zh": summary_readable,
        "failure_examples": failure_examples,
        "results": results,
    }

    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    args.report.write_text(markdown_report, encoding="utf-8")

    print_summary(summary)
    print(f"\nDetailed results written to: {args.output}")
    print(f"Markdown report written to: {args.report}")


if __name__ == "__main__":
    main()
