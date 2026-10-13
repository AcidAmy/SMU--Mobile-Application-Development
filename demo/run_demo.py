#!/usr/bin/env python3
"""
Microsoft MarkItDown 自动化演示脚本
功能：遍历转换常见办公及富文本格式 (Word, Excel, PDF, HTML)，输出转换结果与统计对比。
"""

import os
import sys
import time
from pathlib import Path
from markitdown import MarkItDown

# 终端高亮色彩
GREEN = "\033[92m"
BLUE = "\033[94m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"

def print_banner():
    print(f"""{CYAN}{BOLD}
===============================================================
       Microsoft MarkItDown 功能演示与格式转换流水线
===============================================================
{RESET}""")

def run_conversion_demo():
    print_banner()

    samples_dir = Path(__file__).parent / "samples"
    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    sample_files = [
        ("Word 文档 (.docx)", samples_dir / "document.docx", output_dir / "document.md"),
        ("Excel 表格 (.xlsx)", samples_dir / "financial_table.xlsx", output_dir / "financial_table.md"),
        ("PDF 论文 (.pdf)", samples_dir / "research_paper.pdf", output_dir / "research_paper.md"),
        ("网页文章 (.html)", samples_dir / "web_article.html", output_dir / "web_article.md"),
    ]

    print(f"{BOLD}[1/3] 初始化 MarkItDown 转换引擎...{RESET}")
    md = MarkItDown()
    print(f"{GREEN}✓ 引擎加载就绪！{RESET}\n")

    print(f"{BOLD}[2/3] 开始执行多格式自动化转换：{RESET}")
    total_start = time.time()

    results = []

    for label, src_path, dst_path in sample_files:
        if not src_path.exists():
            print(f"{YELLOW}⚠ 文件未找到，跳过: {src_path}{RESET}")
            continue

        print(f"  ▶ 正在转换: {BOLD}{label}{RESET} ({src_path.name})...", end="", flush=True)
        t0 = time.time()
        try:
            res = md.convert(str(src_path))
            cost = time.time() - t0
            markdown_content = res.markdown or ""
            
            # 保存到输出目录
            dst_path.write_text(markdown_content, encoding="utf-8")
            
            lines_count = len(markdown_content.splitlines())
            chars_count = len(markdown_content)
            
            print(f" {GREEN}成功!{RESET} ({cost:.2f}s | {lines_count} 行 | {chars_count} 字符)")
            results.append({
                "label": label,
                "file": src_path.name,
                "cost": cost,
                "lines": lines_count,
                "chars": chars_count,
                "out": dst_path.name,
                "preview": "\n".join(markdown_content.strip().splitlines()[:6])
            })
        except Exception as e:
            print(f" {YELLOW}失败: {e}{RESET}")

    total_cost = time.time() - total_start
    print(f"\n{BOLD}[3/3] 转换完成，总耗时: {total_cost:.2f} 秒！{RESET}\n")

    print(f"{CYAN}{BOLD}--- 转换效果预览与统计报表 ---{RESET}")
    for item in results:
        print(f"\n{BLUE}▶ 【{item['label']}】 -> 输出文件: demo/output/{item['out']}{RESET}")
        print(f"  耗时: {item['cost']:.2f}s | 产出: {item['lines']} 行 / {item['chars']} 字符")
        print(f"  {YELLOW}Markdown 内容前 6 行预览:{RESET}")
        for line in item['preview'].splitlines():
            print(f"    │ {line[:80]}")
        print("    └──────────────────────────────────────")

    print(f"\n{GREEN}{BOLD}演示顺利结束！所有转换结果已妥善保存在 demo/output/ 文件夹中。{RESET}\n")

if __name__ == "__main__":
    run_conversion_demo()
