import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "site" / "tools"))

import build_data  # noqa: E402


class ExtractFlowTest(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
