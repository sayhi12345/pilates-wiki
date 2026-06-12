import sys
import unittest
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "site" / "tools"))

import build_data  # noqa: E402


class ExtractFlowTest(unittest.TestCase):
    def flow_for(self, source_key, title):
        source = next(source for source in build_data.SOURCES if source["key"] == source_key)
        ocr = build_data.read_ocr(source["ocr"])
        markdown = source["exercise_md"].read_text(encoding="utf-8")
        for block in build_data.section_blocks(markdown):
            block_title, _ = build_data.parse_heading(block["heading"])
            if block_title != title:
                continue
            page_range = build_data.parse_page_range(build_data.parse_field(block["body"], "頁碼"))
            ocr_text = build_data.exercise_ocr_text(ocr, *page_range)
            return build_data.extract_flow(ocr_text, block_title, source["key"])
        self.fail(f"exercise not found: {source_key} {title}")

    def test_keeps_flow_cues_after_interleaved_notes_heading(self):
        ocr_text = "\n".join(
            [
                "用肱三頭肌下壓",
                "練習",
                "吸氣 保持軀幹、肩胛骨和骨盆穩定，彎曲肘關節，將其拉向身",
                "穩定性：軀幹；以大腿骨支撐骨盆；肩胛骨",
                "體兩側。",
                "要點",
                "呼氣 保持肱骨靜止不動，伸展肘關節，將桿朝地板方向下拉。",
                "•準備姿勢為正位站姿，呈中立位分別於矢狀面",
                "吸氣 保持肱骨靜止不動，彎曲肘關節。",
                "肋骨架和腳中心對正排列，膝關節伸直，但不過分伸展）；水平",
                "呼氣 保持穩定，雙臂前伸，恢復初始位置。",
                "面｛髖部和肩部正對前方，雙腿平行）；冠狀面（軀幹兩側等長，",
                "重複練習8-10次。",
                "•保持這種正位，單獨完成肩部和肘部活動",
            ]
        )

        flow = build_data.extract_flow(ocr_text, "用肱三頭肌下壓")

        self.assertIn("體兩側", flow)
        self.assertIn("呼氣 保持肱骨靜止不動", flow)
        self.assertIn("吸氣 保持肱骨靜止不動", flow)
        self.assertIn("呼氣 保持穩定", flow)
        self.assertIn("重複練習8-10次", flow)
        self.assertNotIn("準備姿勢為正位站姿", flow)
        self.assertNotIn("肋骨架和腳中心", flow)
        self.assertNotIn("冠狀面", flow)

    def test_ignores_repeat_count_before_first_flow_cue(self):
        ocr_text = "\n".join(
            [
                "練習",
                "重複練習3-5次",
                "準備，吸氣⋯",
                "呼氣 保持肩胛骨穩定，將框下拉。",
                "吸氣 控制框返回起始位置。",
            ]
        )

        flow = build_data.extract_flow(ocr_text, "背闊肌下拉")

        self.assertTrue(flow.startswith("準備，吸氣"))
        self.assertIn("呼氣 保持肩胛骨穩定", flow)
        self.assertNotEqual("重複練習3-5次", flow)

    def test_reformer_beginner_bend_stretch_skips_page_header_title_and_captions(self):
        flow = self.flow_for("reformer_beginner", "屈伸練習")

        self.assertTrue(flow.startswith("準備，吸氣"))
        self.assertIn("呼氣 雙腿併攏", flow)
        self.assertIn("伸展膝部", flow)
        self.assertIn("吸氣", flow)
        self.assertIn("重複練習10次", flow)
        self.assertNotEqual("屈伸練習 BEND & STRETCH", flow)
        self.assertNotIn("要點［練習1-3］", flow)

    def test_reformer_beginner_short_box_twist_keeps_lines_after_caption_noise(self):
        flow = self.flow_for("reformer_beginner", "扭轉 盒子橫放")

        self.assertTrue(flow.startswith("準備，吸氣"))
        self.assertIn("呼氣 三次", flow)
        self.assertIn("吸氣 伸展脊椎", flow)
        self.assertIn("每側重複練習5次", flow)
        self.assertNotIn("可採取旋轉時吸氣", flow)
        self.assertNotIn("收縮一側腹外斜肌", flow)
        self.assertNotIn("扭轉\n79", flow)

    def test_reformer_intermediate_reverse_expansion_skips_safety_note_before_flow(self):
        flow = self.flow_for("reformer_intermediate", "反向擴張")

        self.assertTrue(flow.startswith("準備，吸氣"))
        self.assertIn("呼氣 用大腿骨支撐骨盆", flow)
        self.assertIn("雙臂前伸", flow)
        self.assertIn("重複練習4次", flow)
        self.assertNotIn("進行，以防練習者身體失衡", flow)
        self.assertNotIn("面向腳踏桿跪在滑墊上", flow)
        self.assertNotIn("雙手套入拉環", flow)

    def test_reformer_intermediate_back_rowing_skips_setup_and_start_position_fragments(self):
        flow = self.flow_for("reformer_intermediate", "後劃")

        self.assertTrue(flow.startswith("準備，吸氣"))
        self.assertIn("呼氣 開始向後捲動", flow)
        self.assertIn("重複練習5次", flow)
        self.assertNotIn("腳踏桿調到4號位", flow)
        self.assertNotIn("雙臂前伸，高度略低於肩部", flow)

    def test_reformer_intermediate_front_splits_skips_start_position_before_flow(self):
        flow = self.flow_for("reformer_intermediate", "前劈叉")

        self.assertTrue(flow.startswith("吸氣"))
        self.assertIn("伸展前膝推開滑墊", flow)
        self.assertNotIn("弓步，面向腳踏桿", flow)
        self.assertNotIn("平衡：弓步姿勢", flow)

    def test_reformer_intermediate_chest_expansion_keeps_start_action_cue(self):
        flow = self.flow_for("reformer_intermediate", "胸部擴張")

        self.assertIn("開始向後拉動雙臂", flow)
        self.assertIn("重複練習6次", flow)

    def test_cadillac_beginner_chest_expansion_keeps_flow_after_title_only_output(self):
        flow = self.flow_for("beginner", "胸部擴張")

        self.assertTrue(flow.startswith("準備，吸氣"))
        self.assertIn("呼氣 保持軀幹穩定", flow)
        self.assertIn("重複練習6次", flow)
        self.assertNotEqual("準備，吸氣⋯", flow)

    def test_cadillac_beginner_leg_springs_bend_stretch_keeps_full_sequence(self):
        flow = self.flow_for("beginner", "腿用彈簧：屈伸練習")

        self.assertTrue(flow.startswith("準備，吸氣"))
        self.assertIn("呼氣 雙腿併攏", flow)
        self.assertIn("吸氣 彎曲膝蓋", flow)
        self.assertIn("重複練習5-10次", flow)

    def test_cadillac_intermediate_knee_raises_skips_principle_fragments(self):
        flow = self.flow_for("intermediate_advanced", "膝部上提")

        self.assertTrue(flow.startswith("準備，吸氣"))
        self.assertIn("呼氣 保持軀幹和雙臂穩定", flow)
        self.assertIn("重複練習5-10次", flow)
        self.assertNotIn("耐力：", flow)

    def test_cadillac_intermediate_scissors_keeps_positioned_leg_instructions(self):
        flow = self.flow_for("intermediate_advanced", "剪刀式")

        self.assertIn("位於上方的腿朝前剪交", flow)
        self.assertIn("位於下方的腿朝後剪交", flow)
        self.assertIn("腿朝前伸展", flow)

    def test_clean_summary_removes_generation_artifacts(self):
        summaries = [
            build_data.clean_summary(
                "胸部擴張：主要歸入核心與腰骨盆穩定；依 OCR 原理/目標肌肉段落整理。"
            ),
            build_data.clean_summary(
                "協調性：主要歸入核心與腰骨盆穩定；依頁面標題、動作說明與動作圖整理。"
            ),
        ]

        self.assertEqual("胸部擴張：主要歸入核心與腰骨盆穩定。", summaries[0])
        self.assertEqual("協調性：主要歸入核心與腰骨盆穩定。", summaries[1])
        self.assertTrue(all("整理" not in summary for summary in summaries))

    def test_reformer_summary_does_not_include_generation_artifact(self):
        exercises = build_data.build_exercises(
            next(source for source in build_data.SOURCES if source["key"] == "reformer_intermediate")
        )

        self.assertTrue(exercises)
        self.assertTrue(all("依 OCR 原理/目標肌肉段落整理" not in exercise["summary"] for exercise in exercises))
        self.assertTrue(all("依頁面標題、動作說明與動作圖整理" not in exercise["summary"] for exercise in exercises))

    def test_clean_flow_puts_prep_breath_on_its_own_line(self):
        flow = build_data.clean_flow_text(
            "上斜方肌：準備，吸氣。呼氣，保持肩胛骨穩定。\n"
            "中斜方肌：準備，吸氣⋯ 呼氣 保持肩胛骨穩定。"
        )

        self.assertEqual(
            [
                "上斜方肌：",
                "準備，吸氣。",
                "呼氣，保持肩胛骨穩定。",
                "中斜方肌：",
                "準備，吸氣⋯",
                "呼氣 保持肩胛骨穩定",
            ],
            flow.splitlines(),
        )

    def test_clean_flow_normalizes_prep_breath_ocr_variants(self):
        flow = build_data.clean_flow_text(
            "準備，級氣⋯\n呼氣 保持肩胛骨穩定。\n"
            "準備，趿氣⋯ 呼氣 保持肩胛骨穩定。\n"
            "準備，明氣1-24：藤找頭\n呼氣 保持姿勢。\n"
            "準備，顧氣：\n呼氣 雙臂前伸。\n"
            "吸氣準備。\n呼氣 保持雙腿伸直。\n"
            "• 準備，吸氣⋯\n呼氣 保持骨盆穩定。"
        )

        self.assertEqual(6, flow.splitlines().count("準備，吸氣⋯"))
        for line in flow.splitlines():
            self.assertNotRegex(line, r"準備，[級趿明顧]氣|吸氣準備")
            if "準備，吸氣" in line:
                self.assertRegex(line, r"^準備，吸氣[.。…⋯：:•]*$")

    def test_generated_flows_put_prep_breath_on_its_own_line(self):
        payload = build_data.build_payload()

        for exercise in payload["exercises"]:
            for line in exercise["flow"].splitlines():
                if not ("準備" in line and ("氣" in line or "汽" in line)):
                    continue
                self.assertRegex(line, r"^準備，吸氣[.。…⋯：:•]*$")

    def test_frontend_prose_splits_prep_breath_ellipsis(self):
        script = r"""
const fs = require("fs");
const code = fs.readFileSync("site/app.js", "utf8");
const start = code.indexOf("function proseSentences");
const end = code.indexOf("function proseSentenceClass");
if (start < 0 || end < 0) throw new Error("proseSentences not found");
eval(code.slice(start, end));
const sentences = proseSentences("準備，吸氣⋯\n呼氣 保持肩胛骨穩定。");
process.stdout.write(JSON.stringify(sentences));
"""
        result = subprocess.run(
            ["node", "-e", script],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            check=True,
        )

        self.assertEqual(
            ["準備，吸氣⋯", "呼氣 保持肩胛骨穩定。"],
            json.loads(result.stdout),
        )

    def test_frontend_prose_treats_prep_breath_as_hard_boundary(self):
        script = r"""
const fs = require("fs");
const code = fs.readFileSync("site/app.js", "utf8");
const start = code.indexOf("function proseSentences");
const end = code.indexOf("function proseSentenceClass");
if (start < 0 || end < 0) throw new Error("proseSentences not found");
eval(code.slice(start, end));
const sentences = proseSentences("上斜方肌：\n準備，吸氣。\n呼氣 保持穩定。\n呼氣 將雙 準備，吸氣⋯\n呼氣 繼續。");
process.stdout.write(JSON.stringify(sentences));
"""
        result = subprocess.run(
            ["node", "-e", script],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            check=True,
        )

        sentences = json.loads(result.stdout)
        prep_sentences = [sentence for sentence in sentences if "準備，吸氣" in sentence]
        self.assertEqual(["準備，吸氣。", "準備，吸氣⋯"], prep_sentences)

    def test_frontend_rendered_generated_flows_put_prep_breath_on_its_own_line(self):
        script = r"""
const fs = require("fs");
const app = fs.readFileSync("site/app.js", "utf8");
const start = app.indexOf("function proseSentences");
const end = app.indexOf("function proseSentenceClass");
if (start < 0 || end < 0) throw new Error("proseSentences not found");
eval(app.slice(start, end));
const raw = fs.readFileSync("site/data.js", "utf8").replace(/^window\.PILATES_DATA = /, "").replace(/;\n$/, "");
const data = JSON.parse(raw);
const bad = [];
for (const exercise of data.exercises) {
  for (const sentence of proseSentences(exercise.flow || "")) {
    if (/準備，吸氣/.test(sentence) && !/^準備，吸氣[.。…⋯：:•]*$/.test(sentence)) {
      bad.push([exercise.id, exercise.title, sentence]);
    }
    if (/準備[，,][級趿明顧雙]氣|吸氣準備/.test(sentence)) {
      bad.push([exercise.id, exercise.title, sentence]);
    }
  }
}
process.stdout.write(JSON.stringify(bad));
"""
        result = subprocess.run(
            ["node", "-e", script],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            check=True,
        )

        self.assertEqual([], json.loads(result.stdout))

    def test_wiki_manual_fields_override_interleaved_ocr(self):
        exercises = build_data.build_exercises(
            next(source for source in build_data.SOURCES if source["key"] == "beginner")
        )
        exercise = next(
            exercise
            for exercise in exercises
            if exercise["english"] == "Roll-Down with Back Extension Prep"
        )

        self.assertIn("雙腿伸直、平行", exercise["startPosition"])
        self.assertIn("重複練習 3-5 次", exercise["flow"])
        self.assertNotIn("始，通過屈曲將脊椎卷離墊", exercise["startPosition"])
        self.assertNotIn("推", exercise["tags"])
        self.assertNotIn("拉", exercise["tags"])
        self.assertNotIn("彈簧", exercise["tags"])

    def test_cadillac_teaser_series_uses_manual_series_flow(self):
        exercises = build_data.build_exercises(
            next(source for source in build_data.SOURCES if source["key"] == "intermediate_advanced")
        )
        exercise = next(
            exercise
            for exercise in exercises
            if exercise["english"] == "TEASER SERIES" and exercise["pageLabel"] == "p.66-71"
        )

        self.assertIn("使用 1 根彈簧", exercise["setup"])
        self.assertIn("臂腿同時", exercise["flow"])
        self.assertIn("單腿調整", exercise["flow"])
        self.assertNotIn("調過位置", exercise["startPosition"])
        self.assertNotIn("彎曲…", exercise["flow"])

    def test_reformer_beginner_hundred_includes_support_sections(self):
        exercises = build_data.build_exercises(
            next(source for source in build_data.SOURCES if source["key"] == "reformer_beginner")
        )
        exercise = next(exercise for exercise in exercises if exercise["title"] == "百次拍擊")

        self.assertIn("目標肌肉", exercise["principles"])
        self.assertIn("長收縮腹直肌", exercise["principles"])
        self.assertIn("耐力", exercise["principles"])
        self.assertIn("全程保持腰椎下沉", exercise["keyPoints"])
        self.assertIn("短促呼吸", exercise["modifications"])
        self.assertNotIn("默數五個數", exercise["principles"])
        self.assertNotIn("重複練習10組", exercise["principles"])

    def test_support_sections_skip_start_position_fragments(self):
        for source_key in ["reformer_beginner", "reformer_intermediate"]:
            with self.subTest(source_key=source_key):
                exercises = build_data.build_exercises(
                    next(source for source in build_data.SOURCES if source["key"] == source_key)
                )
                exercise = next(exercise for exercise in exercises if exercise["title"] == "樹姿 盒子橫放")

                self.assertIn("目標肌肉", exercise["principles"])
                self.assertNotIn("在塑身機盒子上坐直", exercise["principles"])
                self.assertNotIn("一隻腳勾住腳帶", exercise["principles"])
                self.assertNotIn("手握住踝關節", exercise["principles"])
                self.assertNotIn("盒面，或腹肌", exercise["principles"])
                self.assertNotIn("肌輔助腹橫肌運動", exercise["modifications"])
                self.assertNotIn("4. 向後捲動", exercise["modifications"])

    def test_frontend_support_sections_render_closed_by_default(self):
        script = r"""
const fs = require("fs");
const code = fs.readFileSync("site/app.js", "utf8");
const start = code.indexOf("function renderSupportSection");
const end = code.indexOf("function renderDetail");
if (start < 0 || end < 0) throw new Error("renderSupportSection not found");
function escapeHtml(value) {
  return String(value || "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}
function escapeAttr(value) { return escapeHtml(value); }
function proseSentences(value) { return String(value || "").trim() ? [String(value).trim()] : []; }
function proseSentenceClass() { return "prose-sentence"; }
function renderHighlightedSentence(sentence) { return escapeHtml(sentence); }
function renderProse(value) { return `<div>${escapeHtml(value)}</div>`; }
eval(code.slice(start, end));
process.stdout.write(renderSupportSection("原理", "目標肌肉：核心。"));
"""
        result = subprocess.run(
            ["node", "-e", script],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            check=True,
        )

        self.assertIn("<details", result.stdout)
        self.assertIn("原理", result.stdout)
        self.assertNotIn("<details open", result.stdout)


if __name__ == "__main__":
    unittest.main()
