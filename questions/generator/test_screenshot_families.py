#!/usr/bin/env python3
"""Regression tests for the tutorial-screenshot generator families."""

from __future__ import annotations

import json
import random
import re
import tempfile
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator

import deret_angka
import deret_huruf
import kecukupan_data_predikat
from common import load_schema


class ScreenshotFamilyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.bank_dir = Path(self.temp.name)
        self.validator = Draft202012Validator(load_schema())
        self.number = 0

    def tearDown(self) -> None:
        self.temp.cleanup()

    def assert_question(self, path: Path, qtype: str) -> dict:
        question = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual([], list(self.validator.iter_errors(question)))
        self.assertEqual(qtype, question["type"])
        self.assertEqual(5, len({option["text"] for option in question["options"]}))
        self.assertIn(question["correct_option"], "ABCDE")
        return question

    def next_number(self) -> int:
        self.number += 1
        return self.number

    def test_every_letter_family_supports_one_and_two_blanks(self) -> None:
        for index, pattern in enumerate(deret_huruf.EXPLICIT_PATTERNS.values()):
            for blanks in (1, 2):
                path = deret_huruf.build_one(
                    random.Random(100 + index), 1, self.next_number(),
                    self.bank_dir, pattern, blanks, False,
                )
                question = self.assert_question(path, "deret_huruf")
                if blanks == 1:
                    correct_explanation = question["explanations"][question["correct_option"]]
                    self.assertNotIn("Sesudah itu", correct_explanation)
                    self.assertNotIn("Dua huruf berikutnya", correct_explanation)
                    self.assertNotIn("Dua langkah setelah", correct_explanation)

    def test_letter_interior_has_one_square_position_answer(self) -> None:
        path = deret_huruf.build_one(
            random.Random(200), 1, self.next_number(), self.bank_dir,
            None, 1, True,
        )
        question = self.assert_question(path, "deret_huruf")
        correct = next(option["text"] for option in question["options"]
                       if option["key"] == question["correct_option"])
        self.assertEqual("D", correct)
        explanations = " ".join(question["explanations"].values())
        self.assertIn("posisi I", explanations)
        self.assertIn("dari D", explanations)

    def test_new_number_layouts(self) -> None:
        for seed in range(30):
            terms = deret_angka.gen_fixed_four_operation_cycle(random.Random(seed))[0]
            self.assertNotEqual(0, terms[1] % terms[2],
                                "subtraction transition also reads as integer division")
        for blanks in (1, 2):
            path = deret_angka.build_one(
                random.Random(300 + blanks), 2, self.next_number(), self.bank_dir,
                deret_angka.gen_fixed_four_operation_cycle, blanks, False, False,
            )
            self.assert_question(path, "deret_angka")
            path = deret_angka.build_one(
                random.Random(400 + blanks), 2, self.next_number(), self.bank_dir,
                deret_angka.gen_three_interleaved, blanks, False, False,
            )
            self.assert_question(path, "deret_angka")

        path = deret_angka.build_one(
            random.Random(500), 2, self.next_number(), self.bank_dir,
            deret_angka.gen_two_interleaved, 1, False, True,
        )
        question = self.assert_question(path, "deret_angka")
        self.assertTrue(question["question_text"].startswith("..., "))
        printed = question["question_text"].split("Bilangan", 1)[0]
        self.assertEqual(7, len(re.findall(r"−?\d+", printed)))

    def test_predicate_templates_compute_all_five_keys(self) -> None:
        expected = {
            "ratio_vs_sum": "A",
            "sum_vs_equal_denominator": "B",
            "combined_only": "C",
            "each_sufficient": "D",
            "still_insufficient": "E",
        }
        for index, (template, key) in enumerate(expected.items()):
            path = kecukupan_data_predikat.build_one(
                random.Random(600 + index), 3, self.next_number(),
                self.bank_dir, template,
            )
            question = self.assert_question(path, "kecukupan_data")
            self.assertEqual(key, question["correct_option"])


if __name__ == "__main__":
    unittest.main()
