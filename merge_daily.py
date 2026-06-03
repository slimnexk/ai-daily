#!/usr/bin/env python3
"""
merge_daily.py - AI日报合并写入脚本
读取暂存文件 → 合并 → 写入 daily/YYYY-MM-DD.json + 更新 data.json + 生成简报MD

用法:
  python merge_daily.py [--date YYYY-MM-DD] [--repo DIR]

不传 --date 则用今天日期
不传 --repo 则使用默认路径
"""

import json
import sys
import os
from datetime import datetime, timedelta
from pathlib import Path

# 默认仓库路径
DEFAULT_REPO = str(Path.home() / ".qclaw" / "workspace-agent-73f25d14" / "ai-daily")

def main():
    import argparse
    parser = argparse.ArgumentParser(description="合并AI日报暂存文件")
    parser.add_argument("--date", help="目标日期 YYYY-MM-DD，默认今天")
    parser.add_argument("--repo", default=DEFAULT_REPO, help="仓库路径")
    args = parser.parse_args()

    today = args.date or datetime.now().strftime("%Y-%m-%d")
    repo = Path(args.repo)
    briefings_dir = repo / "briefings"

    # 暂存文件路径
    staging_files = {
        "batch1": briefings_dir / "_staging_batch1.json",
        "batch2": briefings_dir / "_staging_batch2.json",
        "batch3": briefings_dir / "_staging_batch3.json",
        "hotsearch": briefings_dir / "_staging_hotsearch.json",
    }

    # 第一步：读取暂存文件
    data = {}
    for key, path in staging_files.items():
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data[key] = json.load(f)
                print(f"[OK] 读取 {key}: {path.name}")
            except Exception as e:
                print(f"[WARN] 读取 {key} 失败: {e}")
                data[key] = None
        else:
            print(f"[SKIP] 跳过 {key}: 文件不存在")
            data[key] = None

    # 第二步：轻量审核
    today_dt = datetime.strptime(today, "%Y-%m-%d")
    cutoff_dt = today_dt - timedelta(days=10)
    seen_titles = set()
    total_removed = 0

    def audit_items(items):
        """审核单条新闻列表"""
        nonlocal total_removed
        if not items:
            return []
        result = []
        for item in items:
            title = item.get("title", "").strip()
            # 去重
            if title in seen_titles:
                total_removed += 1
                continue
            # 时效性检查
            pub_date = item.get("pubDate", "")
            if pub_date:
                try:
                    pd = datetime.strptime(pub_date, "%Y-%m-%d")
                    if pd < cutoff_dt:
                        total_removed += 1
                        continue
                except ValueError:
                    total_removed += 1
                    continue
            # 垃圾过滤（简单关键词）
            junk_keywords = ["带货", "优惠券", "点击领取", "限时免费领"]
            if any(kw in title for kw in junk_keywords):
                total_removed += 1
                continue

            seen_titles.add(title)
            result.append(item)
        return result

    # 第三步：合并
    merged = {}

    # 从 batch1 获取 title/desc/featured
    b1 = data.get("batch1") or {}
    merged["title"] = b1.get("title", f"AI日报 {today}")
    merged["desc"] = b1.get("desc", "")
    merged["featured"] = audit_items(b1.get("featured", []))

    # 热搜
    hs = data.get("hotsearch") or {}
    merged["hotSearch"] = hs.get("hotSearch", [])

    # 各分类
    merged["llm"] = audit_items(b1.get("llm", []))
    merged["github"] = audit_items(b1.get("github", []))
    merged["trend"] = audit_items(b1.get("trend", []))
    merged["world"] = audit_items(b1.get("world", []))

    b2 = data.get("batch2") or {}
    merged["design"] = audit_items(b2.get("design", []))
    merged["video"] = audit_items(b2.get("video", []))
    merged["rag"] = audit_items(b2.get("rag", []))
    merged["devtools"] = audit_items(b2.get("devtools", []))

    b3 = data.get("batch3") or {}
    merged["industry"] = audit_items(b3.get("industry", []))
    merged["game"] = audit_items(b3.get("game", []))
    merged["drama"] = audit_items(b3.get("drama", []))
    merged["apps"] = audit_items(b3.get("apps", []))

    print(f"[AUDIT] 移除 {total_removed} 条（过期/重复/垃圾）")

    # 第四步：写入 daily/TODAY.json
    daily_dir = repo / "daily"
    daily_dir.mkdir(exist_ok=True)
    daily_path = daily_dir / f"{today}.json"
    with open(daily_path, "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)
    print(f"[OK] 写入 {daily_path}")

    # 第五步：更新 data.json
    data_json_path = repo / "data.json"
    if data_json_path.exists():
        with open(data_json_path, "r", encoding="utf-8") as f:
            meta = json.load(f)
    else:
        meta = {"title": "", "desc": "", "dates": {}}

    meta["title"] = merged["title"]
    meta["desc"] = merged["desc"]
    meta.setdefault("dates", {})
    meta["dates"][today] = {
        "title": merged["title"],
        "desc": merged["desc"]
    }

    # 删除30天前的旧日期
    cutoff_30 = (today_dt - timedelta(days=30)).strftime("%Y-%m-%d")
    old_keys = [k for k in meta["dates"] if k < cutoff_30]
    for k in old_keys:
        del meta["dates"][k]

    with open(data_json_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    print(f"[OK] 更新 {data_json_path} (删除 {len(old_keys)} 个旧日期)")

    # 第六步：生成简报MD
    md_lines = [f"# AI百事通 · 每日简报 | {today}\n"]

    def section(emoji, title, items):
        if not items:
            return
        md_lines.append(f"\n## {emoji} {title}\n")
        for item in items:
            t = item.get("title", "")
            d = item.get("desc", "")
            u = item.get("url", "")
            if u:
                md_lines.append(f"- **{t}** — {d} [来源]({u})")
            else:
                md_lines.append(f"- **{t}** — {d}")

    section("🔥", "头条", merged["featured"])

    # 热搜表格
    if merged["hotSearch"]:
        md_lines.append(f"\n## 🔥 热搜榜\n")
        md_lines.append("| 来源 | 热搜 | 热度 |")
        md_lines.append("|------|------|------|")
        for h in merged["hotSearch"]:
            md_lines.append(f"| {h.get('source','')} | {h.get('title','')} | {h.get('heat','')} |")

    section("📊", "大模型动态", merged["llm"])

    # GitHub = github + trend
    section("🛠️", "GitHub热门", merged.get("github", []) + merged.get("trend", []))
    section("🌍", "世界模型", merged.get("world", []))
    section("🎨", "AI设计", merged.get("design", []))
    section("🎬", "视频生成", merged.get("video", []))
    section("📚", "知识库/RAG", merged.get("rag", []))
    section("🔧", "开发工具", merged.get("devtools", []))
    section("💼", "行业资讯", merged.get("industry", []))
    section("🎮", "AI游戏", merged.get("game", []))
    section("🎭", "AI漫剧", merged.get("drama", []))
    section("📱", "AI应用", merged.get("apps", []))

    md_lines.append("\n---\n*每日 9:00 自动更新 | Powered by OpenClaw*")

    md_path = briefings_dir / f"{today}.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines))
    print(f"[OK] 写入 {md_path}")

    print(f"[DONE] 合并完成! 日期={today}, 移除={total_removed}条")

if __name__ == "__main__":
    main()
