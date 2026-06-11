import sys
import unittest
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


if __name__ == "__main__":
    unittest.main()
