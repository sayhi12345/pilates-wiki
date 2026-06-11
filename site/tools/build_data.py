#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SITE = ROOT / "site"

SOURCES = [
    {
        "key": "beginner",
        "label": "初級",
        "exercise_md": ROOT / "wiki" / "exercises" / "cadillac-beginner-exercises.md",
        "ocr": ROOT / "wiki" / "raw" / "cadillac_beginner_ocr_p006-p133.jsonl",
    },
    {
        "key": "intermediate_advanced",
        "label": "中高階",
        "exercise_md": ROOT / "wiki" / "exercises" / "cadillac-intermediate-advanced-exercises.md",
        "ocr": ROOT / "wiki" / "raw" / "cadillac_intermediate_advanced_ocr_p006-p175.jsonl",
    },
    {
        "key": "reformer_beginner",
        "label": "塑身機初級",
        "exercise_md": ROOT / "wiki" / "exercises" / "reformer-beginner-exercises.md",
        "ocr": ROOT / "wiki" / "raw" / "reformer_beginner_ocr_p006-p111.jsonl",
    },
    {
        "key": "reformer_intermediate",
        "label": "塑身機中級",
        "exercise_md": ROOT / "wiki" / "exercises" / "reformer-intermediate-exercises.md",
        "ocr": ROOT / "wiki" / "raw" / "reformer_intermediate_ocr_p006-p163.jsonl",
    },
]

MUSCLE_LABELS = {
    "core": "核心與腰骨盆穩定",
    "spine": "脊椎活動",
    "scapula": "肩胛與上背穩定",
    "lat": "背闊肌與拉力鏈",
    "arms": "手臂與胸肩",
    "hips_legs": "髖與腿",
    "mobility": "柔韌與伸展",
}

GROUP_ALIASES = [
    ("core", ["核心", "腰骨盆", "腹橫肌", "腹直肌", "腹斜肌"]),
    ("spine", ["脊椎", "脊柱", "側屈", "旋轉", "伸展與側屈", "脊椎活動"]),
    ("scapula", ["肩胛", "斜方肌", "前鋸肌", "上背"]),
    ("lat", ["背闊", "大圓肌", "拉力鏈", "肩伸展"]),
    ("arms", ["手臂", "二頭肌", "三頭肌", "胸大肌", "三角肌", "前臂"]),
    ("hips_legs", ["髖", "腿", "臀肌", "胭繩肌", "股四頭", "內收", "外展"]),
    ("mobility", ["柔韌", "伸展", "懸掛", "芭蕾"]),
]

EQUIPMENT_TAGS = [
    "下卷木杆",
    "下卷木桿",
    "推拉框上面彈簧動作",
    "推拉框下面彈簧動作",
    "推拉框站姿",
    "臂用彈簧",
    "臂用彈簧站姿動作",
    "腿用彈簧",
    "腿用彈簧側躺練習",
    "秋千",
    "秋干",
    "水平杠垂掛",
    "毛絨掛帶動作",
    "腳踏桿",
    "彈簧",
    "頭墊",
    "拉環與繩索",
    "塑身機盒子",
    "腳帶",
    "健身板",
    "普拉提塑身機",
]

ACTION_TAG_RULES = [
    ("旋轉", ["旋轉", "扭轉", "TWIST", "OBLIQUES"]),
    ("側屈", ["側屈", "側彎", "SIDE BEND", "MERMAID"]),
    ("伸展", ["伸展", "EXTENSION", "STRETCH", "SWAN", "DEVELOPE"]),
    ("屈曲", ["屈曲", "捲曲", "卷曲", "CURL", "ROLL", "CAT"]),
    ("推", ["推", "PUSH", "PRESS", "PUNCH"]),
    ("拉", ["拉", "PULL", "ROWING", "EXPANSION"]),
    ("懸掛", ["懸掛", "HANG", "水平杠"]),
    ("橋式", ["橋式", "BRIDGE"]),
    ("站姿", ["站姿", "STANDING", "弓步", "LUNGE", "下蹲", "SQUATS"]),
    ("仰臥", ["仰臥", "SUPINE", "ON BACK"]),
    ("俯臥", ["俯臥", "STOMACH"]),
    ("側躺", ["側躺", "SIDE-LYING", "側躺練習"]),
    ("盒上", ["盒子", "BOX", "LONG BOX", "SHORT BOX"]),
    ("跪姿", ["跪", "KNEELING", "KNEE"]),
    ("劈叉", ["劈叉", "SPLITS"]),
    ("腳部系列", ["腳部練習", "FOOTWORK"]),
]


def opencc(text: str) -> str:
    if not text:
        return ""
    converted = subprocess.run(
        ["opencc", "-c", "s2twp.json"],
        input=text,
        text=True,
        stdout=subprocess.PIPE,
        check=True,
    ).stdout
    return (
        converted
        .replace("木杆", "木桿")
        .replace("腳踏杆", "腳踏桿")
        .replace("脚踏桿", "腳踏桿")
        .replace("头墊", "頭墊")
        .replace("秋干", "鞦韆")
        .replace("秋幹", "鞦韆")
        .replace("毛絨掛帶", "絨毛掛帶")
    )


def read_ocr(path: Path) -> dict[int, str]:
    pages: dict[int, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        pages[int(row["page"])] = opencc(row["text"])
    return pages


def slugify(text: str, source_key: str) -> str:
    ascii_part = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    if ascii_part:
        return f"{source_key}-{ascii_part}"
    return f"{source_key}-" + re.sub(r"\s+", "-", text).strip("-")


def parse_page_range(line: str) -> tuple[int, int] | None:
    match = re.search(r"p\.(\d+)(?:-(\d+))?", line)
    if not match:
        return None
    start = int(match.group(1))
    end = int(match.group(2) or start)
    return start, end


def section_blocks(markdown: str) -> list[dict]:
    blocks = re.split(r"\n(?=## )", markdown)
    result = []
    for block in blocks:
        lines = block.strip().splitlines()
        if not lines or not lines[0].startswith("## "):
            continue
        heading = lines[0][3:].strip()
        body = "\n".join(lines[1:])
        result.append({"heading": heading, "body": body})
    return result


def parse_heading(heading: str) -> tuple[str, str]:
    match = re.match(r"(.+?)\s*\(([^()]*)\)\s*$", heading)
    if not match:
        return heading.strip(), ""
    return match.group(1).strip(), match.group(2).strip()


def parse_field(body: str, label: str) -> str:
    match = re.search(rf"^- {re.escape(label)}：(.+)$", body, re.M)
    return match.group(1).strip() if match else ""


def parse_images(body: str) -> list[str]:
    images = []
    for match in re.finditer(r"!\[[^\]]*\]\(([^)]+)\)", body):
        path = match.group(1)
        if path.startswith("../"):
            path = path[3:]
        images.append(f"../wiki/{path}")
    return images


def group_keys(group_text: str) -> list[str]:
    keys = []
    for key, needles in GROUP_ALIASES:
        if any(needle in group_text for needle in needles):
            keys.append(key)
    return list(dict.fromkeys(keys)) or ["core"]


def clean_text(text: str, limit: int = 1100) -> str:
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = text.strip(" ：:；;，,。\\n")
    if len(text) > limit:
        text = text[:limit].rstrip() + "…"
    return text


def clean_summary(text: str) -> str:
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"[；;]?\s*依\s*OCR\s*原理/目標肌肉段落整理。?", "", text)
    text = re.sub(r"[；;]?\s*依頁面標題、動作說明與動作圖整理。?", "", text)
    text = text.strip(" ：:；;，,\\n")
    if text and not text.endswith(("。", "！", "？", ".", "…", "⋯")):
        text += "。"
    return text


def normalized_heading(line: str) -> str:
    return line.strip().strip(" ：:；;，,。…⋯")


def line_after_marker(line: str, markers: list[str]) -> str:
    for marker in markers:
        index = line.find(marker)
        if index >= 0:
            return line[index + len(marker):].lstrip(" ：:；;，,。")
    return ""


def is_breath_or_flow_cue(line: str) -> bool:
    stripped = line.strip()
    return bool(re.match(r"^(準備|吸氣|呼氣|反向|正向|收縮|屈曲|弓步|重複練習|董復練習)", stripped))


def is_flow_cue(line: str) -> bool:
    return bool(
        re.match(
            r"^(準備|開始|接下來|結束動作|過渡|吸氣|呼氣|繼續吸氣|繼續呼氣|正向|反向|屈伸|收縮|弓步|側彎|下蹲)",
            normalized_heading(line),
        )
    )


def is_standard_flow_cue(line: str) -> bool:
    return bool(
        re.match(
            r"^(準備|吸氣|呼氣|正向|反向|屈伸|收縮|弓步|側彎|下蹲)",
            normalized_heading(line),
        )
    )


def is_repeat_line(line: str) -> bool:
    return bool(re.match(r"^(重複練習|董復練習|葷復練習|垂復練習|每側重複練習)", normalized_heading(line)))


def is_standard_repeat_line(line: str) -> bool:
    return bool(re.match(r"^(重複練習|董復練習|每側重複練習)", normalized_heading(line)))


def is_note_line(line: str) -> bool:
    return normalized_heading(line).startswith(("•", "・", "·"))


def ends_sentence(line: str) -> bool:
    return line.strip().endswith(("。", "！", "？", ".", "…", "⋯"))


def is_footer_or_caption(line: str, title: str) -> bool:
    stripped = normalized_heading(line)
    if not stripped:
        return True
    if title and title in stripped:
        return True
    if re.match(r"^\d+\s*[.．、]", stripped):
        return True
    if re.match(r"^\d+\s*練習$", stripped):
        return True
    return any(token in stripped for token in ["merrithew", "PUBLISHING", "出版", "保留所有", "©", "2018", "2019", "CCCC"])


def is_non_flow_line(line: str) -> bool:
    stripped = normalized_heading(line)
    if not stripped:
        return True
    if stripped == "姿勢":
        return True
    return any(
        token in stripped
        for token in [
            "目標肌肉",
            "肌輔助",
            "肌群",
            "向心",
            "離心",
            "收縮上述",
            "穩定性",
            "靈活性",
            "順序",
            "原理",
            "注意事項",
        ]
    )


def is_multicolumn_non_flow_line(line: str) -> bool:
    stripped = normalized_heading(line)
    return is_non_flow_line(line) or any(
        token in stripped
        for token in ["協調性", "耐力", "平衡性", "本體感受"]
    )


def is_setup_line(line: str) -> bool:
    stripped = normalized_heading(line)
    if not stripped or is_breath_or_flow_cue(stripped):
        return False
    return any(
        token in stripped
        for token in [
            "彈簧",
            "腳踏桿",
            "頭墊",
            "拉環",
            "繩索",
            "塑身機盒子",
            "腳帶",
            "滑墊固定栓",
            "木桿",
            "鞦韆",
            "推拉框",
            "掛帶",
            "連線",
            "連附",
            "眼鉤",
            "滑槓",
            "水平槓",
            "立柱",
            "懸掛",
            "安置",
            "安全鏈",
            "毛巾",
        ]
    )


def is_start_line(line: str) -> bool:
    stripped = normalized_heading(line)
    if not stripped or is_breath_or_flow_cue(stripped):
        return False
    if any(
        token in stripped
        for token in [
            "重複練習",
            "返回起始",
            "回到",
            "控制桿返回",
            "下拉",
            "上卷",
            "逐節",
            "情況下開始",
            "胸骨朝",
            "轉離",
            "接觸墊",
            "觸墊後",
            "目標肌肉",
            "肌輔助",
            "肌群",
            "向心",
            "離心",
            "等長",
            "用以",
            "用於",
            "穩定性",
            "靈活性",
            "順序",
        ]
    ):
        return False
    return any(
        token in stripped
        for token in [
            "坐姿",
            "站姿",
            "跪",
            "仰臥",
            "俯臥",
            "側躺",
            "面向",
            "頭部",
            "骨盆",
            "脊椎",
            "雙腿",
            "雙腳",
            "雙臂",
            "雙手",
            "手臂",
            "握住",
            "抓住",
            "肩胛",
            "踝",
            "膝",
            "髖",
            "支撐腿",
            "動作腿",
            "掌心",
            "腳",
            "腿",
            "置於",
            "位置",
            "安置",
            "中立位",
        ]
    )


def is_section_noise(line: str, title: str) -> bool:
    stripped = normalized_heading(line)
    if not stripped:
        return True
    if stripped in {"練習", "起始姿勢", "起姶姿勢", "起始婆勢"}:
        return True
    if stripped.startswith(("要點", "動作調整", "動怍調整", "原理")):
        return True
    if is_footer_or_caption(line, title):
        return True
    if re.fullmatch(r"\d+", stripped):
        return True
    if title and (
        title.replace(" ", "") in stripped.replace(" ", "")
        or (len(stripped) >= 2 and stripped in title)
    ):
        return True
    if re.fullmatch(r"[A-Z][A-Z0-9 &'’/\\:,-]+", stripped):
        return True
    return False


def is_flow_noise_fragment(line: str) -> bool:
    stripped = normalized_heading(line)
    if not stripped:
        return False
    if any(
        token in stripped
        for token in [
            "開始時2根",
        ]
    ):
        return True
    if re.match(r"^(準備|開始|接下來|結束動作|過渡|吸氣|呼氣|繼續吸氣|繼續呼氣|重複練習|董復練習|葷復練習|垂復練習|每側重複練習)", stripped):
        return False
    return any(
        token in stripped
        for token in [
            "腳踏桿調到",
            "頭墊平放",
            "掛1根",
            "掛2根",
            "掛3根",
            "根據個人",
            "仰臥",
            "俯臥",
            "側躺",
            "坐直",
            "面向",
            "背向",
            "跪在",
            "側身站",
            "雙腳抵住",
            "雙踝",
            "蹠屈",
            "雙臂前伸，高度",
            "雙手套入拉環",
            "掌心",
            "手指伸直",
            "骨盆和脊椎保持中立位",
            "脊椎和骨盆保持中立位",
            "大腿骨豎直",
            "懸空，脊椎",
            "虛抱成環形",
            "預留足夠空間",
            "以便到時能使骶骨",
            "貼墊，而不離墊",
            "可採取",
            "收縮一側",
            "收縮靠近",
            "以使脊椎",
            "平衡：",
            "幫助，且手扶",
            "教練不能",
            "應使用防滑墊",
            "練習者可能會",
            "動作調整",
            "動怍調",
            "動作調墊",
            "merrithew",
            "merrieW",
            "PUBLISHING",
            "PUBUSHING",
            "PUBUISHING",
            "初級勸作",
        ]
    )


def extract_setup(text: str) -> str:
    lines = text.splitlines()
    markers = ["裝置安裝", "設備安裝", "沒備安裝", "设备安装", "装置安装"]
    for index, line in enumerate(lines):
        if not any(marker in line for marker in markers):
            continue
        collected = []
        first = line_after_marker(line, markers)
        if first:
            collected.append(first)
        for next_line in lines[index + 1:index + 8]:
            heading = normalized_heading(next_line)
            if heading in {"起始姿勢", "起姶姿勢", "起始婆勢", "原理", "練習"}:
                break
            if is_setup_line(next_line):
                collected.append(next_line.strip())
        return clean_text("\n".join(collected), limit=650)

    for index, line in enumerate(lines):
        if normalized_heading(line) not in {"起始姿勢", "起姶姿勢", "起始婆勢"}:
            continue
        collected = []
        for previous_line in lines[max(0, index - 10):index]:
            if is_setup_line(previous_line):
                collected.append(previous_line.strip())
        return clean_text("\n".join(collected), limit=650)
    return ""


def extract_start_position(text: str) -> str:
    lines = text.splitlines()
    for index, line in enumerate(lines):
        if normalized_heading(line) not in {"起始姿勢", "起姶姿勢", "起始婆勢"}:
            continue
        collected = []
        for next_line in lines[index + 1:index + 16]:
            heading = normalized_heading(next_line)
            if heading in {"練習", "原理", "要點", "動作調整"}:
                break
            if is_start_line(next_line):
                collected.append(next_line.strip())
        return clean_text("\n".join(collected), limit=900)
    return ""


def extract_flow(text: str, title: str, source_key: str = "") -> str:
    if source_key:
        return extract_multicolumn_flow(text, title)

    lines = text.splitlines()
    start_index = None
    for index, line in enumerate(lines):
        if normalized_heading(line) == "練習":
            start_index = index
            break
    if start_index is None:
        return ""
    collected = []
    flow_started = False
    soft_headings = {"要點", "動作調整", "原理"}
    for next_line in lines[start_index + 1:]:
        heading = normalized_heading(next_line)
        if heading in soft_headings:
            continue
        if collected and is_footer_or_caption(next_line, title):
            break
        if is_non_flow_line(next_line) or is_note_line(next_line):
            continue
        cue = is_standard_flow_cue(next_line)
        repeat = is_standard_repeat_line(next_line)
        if not flow_started:
            if not cue:
                continue
            flow_started = True
        elif not cue and not repeat and (not collected or ends_sentence(collected[-1])):
            continue
        collected.append(next_line.strip())
        if repeat:
            break
        if len("\n".join(collected)) >= 1300:
            break
    return clean_text("\n".join(collected), limit=1300)


def extract_multicolumn_flow(text: str, title: str) -> str:
    lines = text.splitlines()
    start_index = None
    for index, line in enumerate(lines):
        if normalized_heading(line) == "練習":
            start_index = index
            break
    if start_index is None:
        return ""
    collected = []
    flow_started = False
    for next_line in lines[start_index + 1:]:
        if is_section_noise(next_line, title):
            continue
        setup_line = is_setup_line(next_line)
        if setup_line and not (flow_started and collected and not ends_sentence(collected[-1])):
            continue
        if is_flow_noise_fragment(next_line):
            continue
        if is_multicolumn_non_flow_line(next_line) or is_note_line(next_line):
            continue
        cue = is_flow_cue(next_line)
        repeat = is_repeat_line(next_line)
        if not flow_started:
            if not cue:
                continue
            flow_started = True
        elif not cue and not repeat and (not collected or ends_sentence(collected[-1])):
            continue
        collected.append(next_line.strip())
        if len("\n".join(collected)) >= 1300:
            break
    return clean_text("\n".join(collected), limit=1300)


def exercise_ocr_text(ocr: dict[int, str], start: int, end: int) -> str:
    return "\n".join(ocr.get(page, "") for page in range(start, end + 1))


def tags_for(exercise: dict, ocr_text: str) -> list[str]:
    haystack = f"{exercise['title']} {exercise['english']} {exercise['equipment']} {exercise['summary']} {ocr_text[:900]}".upper()
    tags = [exercise["sourceLabel"]]
    if exercise.get("difficulty"):
        tags.append(exercise["difficulty"])
    for key in exercise["muscleKeys"]:
        tags.append(MUSCLE_LABELS[key])
    for equipment in EQUIPMENT_TAGS:
        if equipment.upper() in haystack:
            tags.append(opencc(equipment))
    for tag, needles in ACTION_TAG_RULES:
        if any(needle.upper() in haystack for needle in needles):
            tags.append(tag)
    return list(dict.fromkeys(tag for tag in tags if tag))


def build_exercises(source: dict) -> list[dict]:
    markdown = source["exercise_md"].read_text(encoding="utf-8")
    ocr = read_ocr(source["ocr"])
    exercises = []
    for block in section_blocks(markdown):
        title, english = parse_heading(block["heading"])
        page_range = parse_page_range(parse_field(block["body"], "頁碼"))
        if not page_range:
            continue
        start, end = page_range
        group_text = parse_field(block["body"], "肌群分類")
        difficulty = parse_field(block["body"], "難度")
        equipment = parse_field(block["body"], "器械/章節")
        summary = clean_summary(parse_field(block["body"], "摘要"))
        images = parse_images(block["body"])
        full_ocr = exercise_ocr_text(ocr, start, end)
        setup = extract_setup(full_ocr)
        start_position = extract_start_position(full_ocr)
        flow = extract_flow(full_ocr, title, source["key"])
        muscle_keys = group_keys(group_text)
        exercise = {
            "id": slugify(english or title, source["key"]),
            "source": source["key"],
            "sourceLabel": source["label"],
            "title": title,
            "english": english,
            "pageStart": start,
            "pageEnd": end,
            "pageLabel": f"p.{start}" if start == end else f"p.{start}-{end}",
            "difficulty": difficulty or source["label"],
            "equipment": equipment or infer_equipment(title, full_ocr),
            "muscleKeys": muscle_keys,
            "muscles": [MUSCLE_LABELS[key] for key in muscle_keys],
            "summary": summary,
            "setup": setup,
            "startPosition": start_position,
            "flow": flow,
            "images": images,
        }
        exercise["tags"] = tags_for(exercise, full_ocr)
        exercises.append(exercise)
    return exercises


def infer_equipment(title: str, text: str) -> str:
    haystack = f"{title}\n{text[:800]}"
    for equipment in EQUIPMENT_TAGS:
        if equipment in haystack:
            return opencc(equipment)
    return "未標明"


def build_payload() -> dict:
    exercises = []
    for source in SOURCES:
        exercises.extend(build_exercises(source))
    tag_counts: dict[str, int] = {}
    for exercise in exercises:
        for tag in exercise["tags"]:
            tag_counts[tag] = tag_counts.get(tag, 0) + 1
    return {
        "muscleGroups": [{"key": key, "label": label} for key, label in MUSCLE_LABELS.items()],
        "exercises": exercises,
        "tagCounts": dict(sorted(tag_counts.items(), key=lambda item: (-item[1], item[0]))),
    }


def main() -> None:
    SITE.mkdir(exist_ok=True)
    payload = build_payload()
    data = json.dumps(payload, ensure_ascii=False, indent=2)
    (SITE / "data.js").write_text("window.PILATES_DATA = " + data + ";\n", encoding="utf-8")
    print(f"wrote site/data.js exercises={len(payload['exercises'])} tags={len(payload['tagCounts'])}")


if __name__ == "__main__":
    main()
