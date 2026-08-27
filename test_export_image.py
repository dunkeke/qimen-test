"""Regression tests for the one-image Qi Men + AI report export."""

from io import BytesIO
import unittest

from PIL import Image

from export_image import WIDTH, _clean_markdown, _reading_blocks, generate_qimen_report_png


def sample_pan() -> dict:
    palaces = {str(index): value for index, value in enumerate("蓬任冲辅英芮柱心禽", start=1)}
    return {
        "basicInfo": {"date": "2026-06-05 16:52"},
        "juShu": {"fullName": "阳遁三局"},
        "zhiFuGong": "8",
        "zhiShiGong": "2",
        "maStar": {"gong": "6"},
        "baShen": {str(index): "值符" if index == 8 else "九天" for index in range(1, 10)},
        "jiuXing": palaces,
        "baMen": {str(index): value for index, value in enumerate("休死伤杜中开惊生景", start=1)},
        "tianPan": {str(index): value for index, value in enumerate("戊己庚辛壬癸丁丙乙", start=1)},
        "diPan": {str(index): value for index, value in enumerate("乙丙丁戊己庚辛壬癸", start=1)},
        "anGan": {str(index): value for index, value in enumerate("壬癸丁丙乙戊己庚辛", start=1)},
        "siHai": {
            "byGong": {
                "2": [{"type": "空亡"}, {"type": "入墓"}],
                "8": [{"type": "击刑"}, {"type": "入墓"}],
                "9": [{"type": "门迫"}],
            },
            "summary": {
                "counts": {"空亡": 1, "门迫": 1, "击刑": 1, "入墓": 2},
                "total": 5,
                "affectedGongs": ["2", "8", "9"],
            },
        },
    }


class ExportImageTest(unittest.TestCase):
    def test_markdown_is_cleaned_but_structure_is_preserved(self) -> None:
        self.assertEqual(_clean_markdown("**重点**与[依据](https://example.com)"), "重点与依据")
        self.assertEqual(_reading_blocks("## 结论\n- 谨慎推进")[:2], [("heading", "结论"), ("body", "• 谨慎推进")])

    def test_png_contains_full_dynamic_report(self) -> None:
        reading = "## 1. 盘面要点\n" + "此宫信息需要结合四害与值符判断。" * 80 + "\n\n- 建议分阶段推进。"
        payload = generate_qimen_report_png(sample_pan(), "未来三个月项目推进需要注意什么？", reading)
        self.assertTrue(payload.startswith(b"\x89PNG\r\n\x1a\n"))
        with Image.open(BytesIO(payload)) as image:
            self.assertEqual(image.width, WIDTH)
            self.assertGreater(image.height, 2300)
            self.assertEqual(image.mode, "RGB")
            image.verify()


if __name__ == "__main__":
    unittest.main()
