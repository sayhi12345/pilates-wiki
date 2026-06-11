#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import subprocess
from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
WIKI = ROOT / "wiki"


GROUPS = {
    "core": {
        "title": "核心與腰骨盆穩定",
        "file_suffix": "core-and-lumbopelvic-stability.md",
        "desc": "腹橫肌、骨盆底、腹直肌、腹斜肌、多裂肌，以及滑墊移動時的腰骨盆控制。",
    },
    "spine": {
        "title": "脊椎活動",
        "file_suffix": "spinal-articulation.md",
        "desc": "脊椎屈曲、伸展、旋轉與側屈，包括短脊椎、長脊椎、盒上系列與美人魚。",
    },
    "scapula": {
        "title": "肩胛與上背穩定",
        "file_suffix": "scapular-stabilizers.md",
        "desc": "肩胛骨貼合肋骨架、避免上提或外翻，並配合上背穩定肌群控制拉環與腳踏桿。",
    },
    "lat": {
        "title": "背闊肌與拉力鏈",
        "file_suffix": "lat-teres-pulling-chain.md",
        "desc": "背闊肌、大圓肌、後三角肌與肩伸展/內收控制，常見於拉環、划船與胸部擴張。",
    },
    "arms": {
        "title": "手臂與胸肩",
        "file_suffix": "arms-delts-pecs.md",
        "desc": "二頭肌、肱三頭肌、前三角肌、胸大肌、旋轉袖與手臂推拉系列。",
    },
    "hips_legs": {
        "title": "髖與腿",
        "file_suffix": "hips-and-legs.md",
        "desc": "臀大肌、股後肌群、股四頭肌、內收/外展肌、髖屈肌與腳部/腿部系列。",
    },
    "mobility": {
        "title": "柔韌與伸展",
        "file_suffix": "mobility-and-stretching.md",
        "desc": "髖屈肌、股後肌群、內收肌、背闊肌與側線伸展，並以穩定控制活動範圍。",
    },
}


@dataclass(frozen=True)
class Source:
    slug: str
    label: str
    title: str
    pdf: str
    total_pages: int
    start_page: int
    end_page: int
    exercise_start: int
    exercise_end: int
    ocr: Path
    actions: Path
    exercise_file: str
    source_file: str
    muscle_prefix: str


SOURCES = [
    Source(
        slug="reformer_beginner",
        label="塑身機初級",
        title="普拉提塑身機初級",
        pdf="a塑身机初级扫描.pdf",
        total_pages=116,
        start_page=6,
        end_page=111,
        exercise_start=28,
        exercise_end=108,
        ocr=WIKI / "raw" / "reformer_beginner_ocr_p006-p111.jsonl",
        actions=WIKI / "raw" / "reformer_beginner_action_regions.json",
        exercise_file="reformer-beginner-exercises.md",
        source_file="reformer_beginner_source.md",
        muscle_prefix="reformer-beginner",
    ),
    Source(
        slug="reformer_intermediate",
        label="塑身機中級",
        title="普拉提塑身機中級",
        pdf="a_普拉提塑身机中级.pdf",
        total_pages=168,
        start_page=6,
        end_page=163,
        exercise_start=28,
        exercise_end=161,
        ocr=WIKI / "raw" / "reformer_intermediate_ocr_p006-p163.jsonl",
        actions=WIKI / "raw" / "reformer_intermediate_action_regions.json",
        exercise_file="reformer-intermediate-exercises.md",
        source_file="reformer_intermediate_source.md",
        muscle_prefix="reformer-intermediate",
    ),
]


def opencc(text: str) -> str:
    if not text:
        return ""
    result = subprocess.run(
        ["opencc", "-c", "s2twp.json"],
        input=text,
        text=True,
        stdout=subprocess.PIPE,
        check=True,
    ).stdout
    return (
        result.replace("塑身机", "塑身機")
        .replace("滑垫", "滑墊")
        .replace("脚踏杆", "腳踏桿")
        .replace("头垫", "頭墊")
        .replace("拉环", "拉環")
        .replace("股后肌群", "股後肌群")
        .replace("跖球部", "蹠球部")
    )


def read_ocr(source: Source) -> dict[int, str]:
    pages = {}
    for line in source.ocr.read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        pages[int(row["page"])] = row["text"]
    return pages


def read_actions(source: Source) -> dict[int, list[str]]:
    actions: dict[int, list[str]] = defaultdict(list)
    for row in json.loads(source.actions.read_text(encoding="utf-8")):
        for region in row["regions"]:
            actions[int(row["page"])].append(region["file"])
    return dict(actions)


def clean_line(line: str) -> str:
    return re.sub(r"\s+", " ", line).strip(" ：:;；•-』」'\"")


def normalize_english(text: str) -> str:
    text = re.sub(r"\bCONTINUED\b|\b续\b", "", text.upper())
    text = re.sub(r"[^A-Z0-9&' ,.-]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip(" ,.-")
    replacements = {
        "SITING": "SITTING",
        "TWSI": "TWIST",
        "HP LFT": "HIP LIFT",
        " LFT": " LIFT",
        "PREP.": "PREP",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text


def split_title_english(line: str) -> tuple[str, str]:
    line = clean_line(line).replace("：", " ")
    line = re.sub(r"\s*[续續]\s*$", "", line)
    match = re.search(r"([A-Z][A-Z0-9&' ,.-]{2,})$", line)
    if not match:
        return line.replace("续", "").strip(), ""
    title = clean_line(line[: match.start()]).replace("续", "").strip()
    english = normalize_english(match.group(1))
    return title or line, english


def canonical_title(title: str) -> str:
    title = re.sub(r"[A-Z0-9&' -]+", "", title)
    title = re.sub(r"[續续：:；;，,。．\s]+", "", title)
    return title


def is_bad_title(title: str) -> bool:
    stripped = title.strip()
    if not stripped:
        return True
    if stripped in {"*", "＊"}:
        return True
    if re.match(r"^(準備|准备|吸氣|吸气|呼氣|呼气|正向|接下來|接下来|重複|重复)", stripped):
        return True
    return any(
        token in stripped
        for token in [
            "第22页",
            "第22頁",
            "要点",
            "要點",
            "脚踏杆",
            "腳踏杆",
            "腳踏桿",
            "彈簧",
            "弹簧",
            "注意事项",
            "注意事項",
            "雙臂前伸",
            "双臂前伸",
            "骨盆保持",
            "侧身站",
            "側身站",
            "进行，以防",
            "進行，以防",
            "起始姿",
            "推開滑墊",
            "推开滑垫",
            "控制滑墊",
            "控制滑垫",
            "目標肌肉",
            "目标肌肉",
            "動作調整",
            "动作调整",
        ]
    )


def is_english_line(line: str) -> bool:
    normalized = normalize_english(line)
    return len(normalized) >= 3 and normalized == re.sub(r"\s+", " ", line.upper()).strip(" ：:;；'\"")


def parse_heading(page: int, text: str, source: Source) -> dict | None:
    if page < source.exercise_start or page > source.exercise_end:
        return None
    lines = [clean_line(line) for line in text.splitlines() if clean_line(line)]
    if not lines:
        return None
    top = lines[:12]
    if any("列表" in line for line in top[:4]):
        return None

    try:
        marker = next(i for i, line in enumerate(top[:5]) if line in {"练习", "練習"} or line.startswith("练习 ") or line.startswith("練習 "))
    except StopIteration:
        return None

    inline_title = re.sub(r"^(练习|練習)\s+", "", top[marker]).strip()
    inline_candidates = [inline_title] if inline_title and inline_title not in {"动作", "動作"} else []
    candidates = [
        line
        for line in [*inline_candidates, *top[marker + 1 : marker + 7]]
        if line not in {"•", "原理", "要点", "要點", "练习", "練習"} and not is_bad_title(line)
    ]
    if not candidates:
        return None

    title = ""
    english = ""
    for index, line in enumerate(candidates):
        if is_english_line(line):
            continue
        if re.match(r"^\d+[.．、]\s*", line) and not title:
            continue
        title, english = split_title_english(line)
        if not english and index + 1 < len(candidates) and is_english_line(candidates[index + 1]):
            english = normalize_english(candidates[index + 1])
        if title and title not in {"练习", "練習", "原理", "要点", "要點"} and not is_bad_title(title):
            break

    title = re.sub(r"^\d+[.．、]\s*", "", title).strip()
    if is_bad_title(title) or len(title) > 34:
        return None

    continuation = "续" in " ".join(top[:8]) or "續" in " ".join(top[:8])
    return {
        "page": page,
        "title": title,
        "english": english,
        "continuation": continuation,
    }


def detected_exercises(source: Source, ocr: dict[int, str]) -> list[dict]:
    starts = []
    for page in range(source.exercise_start, source.exercise_end + 1):
        heading = parse_heading(page, ocr.get(page, ""), source)
        if heading:
            starts.append(heading)

    exercises: list[dict] = []
    for start in starts:
        key = normalize_english(start["english"]) or start["title"]
        if exercises:
            prev = exercises[-1]
            prev_key = normalize_english(prev["english"]) or prev["title"]
            start_title_key = canonical_title(start["title"])
            prev_title_key = canonical_title(prev["title"])
            same_series = (
                key == prev_key
                or (start_title_key and prev_title_key and (start_title_key == prev_title_key or start_title_key in prev_title_key or prev_title_key in start_title_key))
            )
            if same_series:
                prev["detected_pages"].append(start["page"])
                prev["end"] = start["page"]
                continue
        exercises.append({**start, "start": start["page"], "end": start["page"], "detected_pages": [start["page"]]})

    for index, exercise in enumerate(exercises):
        if index + 1 < len(exercises):
            exercise["end"] = max(exercise["end"], exercises[index + 1]["start"] - 1)
        else:
            exercise["end"] = source.exercise_end
    return exercises


def exercise_text(exercise: dict, ocr: dict[int, str]) -> str:
    return "\n".join(ocr.get(page, "") for page in range(exercise["start"], exercise["end"] + 1))


def target_excerpt(text: str) -> str:
    compact = re.sub(r"\s+", " ", text)
    found = re.search(r"(目标肌肉|日标肌肉|目標肌肉|原理)[：:；; ](.{0,360})", compact)
    if not found:
        return ""
    excerpt = found.group(2)
    stop = re.search(r"(稳定性|穩定性|灵活性|靈活性|要点|要點|动作调整|動作調整|起始姿势|起始姿勢)", excerpt)
    if stop:
        excerpt = excerpt[: stop.start()]
    return clean_text(opencc(excerpt), 420)


def classify(exercise: dict, text: str, excerpt: str) -> list[str]:
    haystack = f"{exercise['title']} {exercise['english']} {text[:1300]} {excerpt}"
    rules = [
        ("core", ["腹横", "骨盆底", "腹直", "腹斜", "多裂", "腰骨盆", "百次", "HUNDRED"]),
        ("spine", ["脊椎", "脊柱", "竖脊", "屈曲", "伸展", "旋转", "扭转", "卷曲", "短脊椎", "长脊椎", "SHORT SPINE", "LONG SPINE", "TWIST", "ROUND BACK"]),
        ("scapula", ["肩胛", "斜方", "前锯", "菱形", "肩带", "划", "ROWING"]),
        ("lat", ["背阔", "大圆", "胸部扩张", "拉动拉环", "PULLING STRAPS", "CHEST EXPANSION", "ROWING"]),
        ("arms", ["二头", "肱三头", "三角", "胸大", "手臂", "肘", "内旋", "外旋", "内收", "外展", "BICEPS", "TRICEPS", "ARMS", "SALUTE", "OFFERING"]),
        ("hips_legs", ["臀大", "股后", "胭绳", "髋", "股四", "腿", "膝", "踝", "脚部", "单腿", "劈叉", "FOOTWORK", "SINGLE LEG", "LEG", "SPLITS", "KNEE", "RUNNING"]),
        ("mobility", ["伸展", "美人鱼", "劈叉", "树姿", "拉伸", "STRETCH", "MERMAID", "TREE", "SPLITS"]),
    ]
    groups = []
    for group, needles in rules:
        if any(needle in haystack for needle in needles):
            groups.append(group)
    return list(dict.fromkeys(groups)) or ["core"]


def clean_text(text: str, limit: int = 900) -> str:
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = text.strip(" ：:；;，,。⋯…\n")
    if len(text) > limit:
        text = text[:limit].rstrip() + "…"
    return text


def infer_equipment(text: str) -> str:
    haystack = text[:1200]
    items = []
    if "脚踏杆" in haystack:
        items.append("腳踏桿")
    if "弹簧" in haystack:
        items.append("彈簧")
    if "头垫" in haystack:
        items.append("頭墊")
    if "拉环" in haystack or "绳索" in haystack:
        items.append("拉環與繩索")
    if "盒子" in haystack:
        items.append("塑身機盒子")
    if "脚带" in haystack:
        items.append("腳帶")
    if "跳板" in haystack or "健身板" in haystack:
        items.append("健身板")
    return "、".join(dict.fromkeys(items)) or "普拉提塑身機"


def summary_for(exercise: dict, groups: list[str], excerpt: str) -> str:
    group_names = "、".join(GROUPS[group]["title"] for group in groups[:4])
    if excerpt:
        return f"{opencc(exercise['title'])}：主要歸入{group_names}；依 OCR 原理/目標肌肉段落整理。"
    return f"{opencc(exercise['title'])}：主要歸入{group_names}；依頁面標題、動作說明與動作圖整理。"


def page_range_text(start: int, end: int) -> str:
    return f"p.{start}" if start == end else f"p.{start}-{end}"


def exercise_images(exercise: dict, actions: dict[int, list[str]]) -> list[str]:
    files: list[str] = []
    for page in range(exercise["start"], exercise["end"] + 1):
        files.extend(actions.get(page, []))
    return files


def rel_from(doc_dir: Path, target: str) -> str:
    target = target.removeprefix("wiki/")
    return Path(target).as_posix() if doc_dir == WIKI else "../" + target


def muscle_file(source: Source, group: str) -> str:
    return f"{source.muscle_prefix}-{GROUPS[group]['file_suffix']}"


def build_source(source: Source) -> list[dict]:
    ocr = read_ocr(source)
    actions = read_actions(source)
    exercises = detected_exercises(source, ocr)

    for exercise in exercises:
        text = exercise_text(exercise, ocr)
        excerpt = target_excerpt(text)
        groups = classify(exercise, text, excerpt)
        exercise["title_tw"] = opencc(exercise["title"])
        exercise["english"] = normalize_english(exercise.get("english", ""))
        exercise["groups"] = groups
        exercise["excerpt"] = excerpt
        exercise["summary"] = summary_for(exercise, groups, excerpt)
        exercise["equipment"] = infer_equipment(text)
        exercise["images"] = exercise_images(exercise, actions)

    write_source_note(source, ocr, actions, exercises)
    write_exercise_catalog(source, exercises)
    write_group_pages(source, exercises)
    return exercises


def write_source_note(source: Source, ocr: dict[int, str], actions: dict[int, list[str]], exercises: list[dict]) -> None:
    out = WIKI / "sources"
    out.mkdir(exist_ok=True)
    total_regions = sum(len(v) for v in actions.values())
    skipped_last_start = source.end_page + 1
    lines = [
        f"# {source.title} source note",
        "",
        f"- 原始文件：`{source.pdf}`",
        f"- PDF 總頁數：{source.total_pages}",
        f"- 處理範圍：第 {source.start_page}-{source.end_page} 頁，跳過首 5 頁和末 5 頁。",
        f"- OCR 文字：`wiki/raw/{source.ocr.name}`，共 {len(ocr)} 頁。",
        f"- 動作截圖 manifest：`wiki/raw/{source.actions.name}`，共 {len(actions)} 頁、{total_regions} 個裁切區域。",
        f"- 截圖目錄：`wiki/assets/{source.slug}_actions/`",
        f"- 整理動作條目：{len(exercises)} 個。",
        "",
        "## 頁面範圍",
        "",
        f"- p.{source.start_page}-{source.exercise_start - 1}：前言、基本原則、常見調整與塑身機安全/使用說明。",
        f"- p.{source.exercise_start}-{source.exercise_end}：{source.label}動作說明。",
        f"- p.{skipped_last_start}-{source.total_pages}：依規格略過。",
        "",
        "## OCR 注意",
        "",
        "這份 PDF 是橫向掃描件，原始文字層不可直接使用。Wiki 內容以 macOS Vision OCR 為基礎，再轉為繁體中文；少數中文詞、英文標題或頁面批註可能仍需人工複核。",
        "",
    ]
    (out / source.source_file).write_text("\n".join(lines), encoding="utf-8")


def write_exercise_catalog(source: Source, exercises: list[dict]) -> None:
    out = WIKI / "exercises"
    out.mkdir(exist_ok=True)
    lines = [
        f"# {source.title}動作索引",
        "",
        f"來源：[[../sources/{Path(source.source_file).stem}|{source.title} source note]]。",
        "",
        f"範圍：PDF 第 {source.start_page}-{source.end_page} 頁；已按要求跳過首 5 頁和末 5 頁。",
        "",
    ]
    for exercise in exercises:
        group_links = ", ".join(
            f"[[../muscles/{Path(muscle_file(source, group)).stem}|{GROUPS[group]['title']}]]"
            for group in exercise["groups"]
        )
        title = exercise["title_tw"]
        english = f" ({exercise['english']})" if exercise["english"] else ""
        lines.extend(
            [
                f"## {title}{english}",
                "",
                f"- 頁碼：{page_range_text(exercise['start'], exercise['end'])}",
                f"- 難度：{source.label}",
                f"- 器械/章節：{exercise['equipment']}",
                f"- 肌群分類：{group_links}",
                f"- 摘要：{exercise['summary']}",
            ]
        )
        if exercise["excerpt"]:
            lines.append(f"- OCR 原文摘錄：{exercise['excerpt']}")
        if exercise["images"]:
            lines.append("- 動作圖：")
            for image in exercise["images"]:
                lines.append(f"  - ![]({rel_from(out, image)})")
        lines.append("")
    (out / source.exercise_file).write_text("\n".join(lines), encoding="utf-8")


def write_group_pages(source: Source, exercises: list[dict]) -> None:
    out = WIKI / "muscles"
    out.mkdir(exist_ok=True)
    by_group: dict[str, list[dict]] = defaultdict(list)
    for exercise in exercises:
        for group in exercise["groups"]:
            by_group[group].append(exercise)

    for group, meta in GROUPS.items():
        lines = [
            f"# {source.label}：{meta['title']}",
            "",
            meta["desc"],
            "",
            "## 整理原則",
            "",
            "- 依 OCR 的原理/目標肌肉段落、動作標題與頁面動作圖共同分類。",
            "- 若同一系列包含多個編號變化，保留為同一條目，避免拆散教學上下文。",
            "",
            "## 相關動作",
            "",
        ]
        for exercise in by_group[group]:
            title = exercise["title_tw"]
            english = f" ({exercise['english']})" if exercise["english"] else ""
            lines.extend(
                [
                    f"### {title}{english}",
                    "",
                    f"- 頁碼：{page_range_text(exercise['start'], exercise['end'])}",
                    f"- 器械/章節：{exercise['equipment']}",
                    f"- 摘要：{exercise['summary']}",
                    f"- 動作索引：[[../exercises/{Path(source.exercise_file).stem}#{title.replace(' ', '-')}|查看完整條目]]",
                ]
            )
            if exercise["images"]:
                lines.append(f"- 代表圖：![]({rel_from(out, exercise['images'][0])})")
            lines.append("")
        (out / muscle_file(source, group)).write_text("\n".join(lines), encoding="utf-8")


def update_index(all_counts: dict[str, int]) -> None:
    path = WIKI / "index.md"
    text = path.read_text(encoding="utf-8")
    source_block = "\n".join(
        [
            "- [[sources/reformer_beginner_source|普拉提塑身機初級 source note]]：處理範圍、OCR、截圖 manifest、全頁影像連結。",
            "- [[sources/reformer_intermediate_source|普拉提塑身機中級 source note]]：處理範圍、OCR、截圖 manifest、全頁影像連結。",
            "- `a塑身机初级扫描.pdf`：原始 PDF。",
            "- `a_普拉提塑身机中级.pdf`：原始 PDF。",
        ]
    )
    catalog_block = "\n".join(
        [
            "- [[exercises/reformer-beginner-exercises|普拉提塑身機初級動作索引]]：依頁碼列出塑身機初級動作，附肌群分類與動作圖。",
            "- [[exercises/reformer-intermediate-exercises|普拉提塑身機中級動作索引]]：依頁碼列出塑身機中級動作，附肌群分類與動作圖。",
        ]
    )
    if "reformer_beginner_source" not in text:
        text = text.replace("- `凯迪拉克中高级.pdf`：原始 PDF。", "- `凯迪拉克中高级.pdf`：原始 PDF。\n" + source_block)
    if "reformer-beginner-exercises" not in text:
        text = text.replace("- [[exercises/cadillac-intermediate-advanced-exercises|凱迪拉克中高階動作索引]]：依頁碼列出中級/高階動作，附肌群分類與動作圖。", "- [[exercises/cadillac-intermediate-advanced-exercises|凱迪拉克中高階動作索引]]：依頁碼列出中級/高階動作，附肌群分類與動作圖。\n" + catalog_block)
    note = (
        f"- 普拉提塑身機初級：已跳過 PDF 第 1-5 頁與第 112-116 頁；整理 {all_counts['reformer_beginner']} 個動作條目。\n"
        f"- 普拉提塑身機中級：已跳過 PDF 第 1-5 頁與第 164-168 頁；整理 {all_counts['reformer_intermediate']} 個動作條目。"
    )
    if "普拉提塑身機初級：已跳過" not in text:
        text = text.rstrip() + "\n" + note + "\n"
    path.write_text(text, encoding="utf-8")


def update_log(all_counts: dict[str, int]) -> None:
    path = WIKI / "log.md"
    text = path.read_text(encoding="utf-8")
    if "ingest | 普拉提塑身機初級 / 中級" in text:
        return
    lines = [
        "",
        f"## [{date.today().isoformat()}] ingest | 普拉提塑身機初級 / 中級",
        "",
        "- 依使用者要求沿用既有處理方式，兩份 PDF 均跳過首 5 頁與末 5 頁。",
        "- 初級處理 PDF 第 6-111 頁；中級處理 PDF 第 6-163 頁。",
        "- 使用 `pdftoppm` 渲染橫向掃描頁，使用 macOS Vision OCR 產生中文 OCR JSONL，再轉為繁體中文整理。",
        "- 自動裁切動作圖並寫入 `wiki/assets/reformer_beginner_actions/` 與 `wiki/assets/reformer_intermediate_actions/`。",
        f"- 建立塑身機 source note、動作索引與肌肉/肌群分類頁；初級 {all_counts['reformer_beginner']} 個條目，中級 {all_counts['reformer_intermediate']} 個條目。",
        "",
    ]
    path.write_text(text.rstrip() + "\n" + "\n".join(lines), encoding="utf-8")


def main() -> None:
    counts = {}
    for source in SOURCES:
        exercises = build_source(source)
        counts[source.slug] = len(exercises)
        print(f"{source.slug}: exercises={len(exercises)}")
    update_index(counts)
    update_log(counts)


if __name__ == "__main__":
    main()
