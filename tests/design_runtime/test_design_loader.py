from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from vassago_contract_runtime.design_runtime.design_loader import DesignLoadError, load_design, parse_simple_yaml


class DesignLoaderTests(unittest.TestCase):
    def test_parse_sc01_design_yaml(self) -> None:
        design = load_design(Path("designs") / "sc01-access" / "design.yaml")

        self.assertEqual(design.design_id, "sc01-access")
        self.assertEqual(len(design.phases), 11)
        self.assertEqual(design.phases[0].phase_id, "00_intake")
        self.assertEqual(design.phases[-1].phase_id, "10_final_report")
        self.assertEqual(design.phases[8].gate.gate_id, "compile_ready")

    def test_parse_simple_yaml_supports_nested_list_of_maps(self) -> None:
        payload = parse_simple_yaml(
            """
id: demo
flags:
  enabled: true
phases:
  - id: "00_one"
    name: One
    outputs:
      - one.json
      - two.md
"""
        )

        self.assertTrue(payload["flags"]["enabled"])
        self.assertEqual(payload["phases"][0]["outputs"], ["one.json", "two.md"])

    def test_invalid_design_raises_design_load_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "design.yaml"
            path.write_text("id: bad\nversion: v1\n", encoding="utf-8")

            with self.assertRaises(DesignLoadError) as error:
                load_design(path)

        self.assertEqual(error.exception.code, "invalid_design_title")


if __name__ == "__main__":
    unittest.main()
