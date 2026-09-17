"""Run with: python3 -B -m unittest discover -s scripts -p 'test_*.py'."""

import json
import shutil
import subprocess
import unittest

from import_blogger import convert_html_to_markdown


@unittest.skipUnless(shutil.which("pandoc"), "pandoc is required")
class MathImportTests(unittest.TestCase):
    def math_nodes(self, source):
        markdown = convert_html_to_markdown("pandoc", source)
        document = json.loads(subprocess.check_output(
            ["pandoc", "-f", "markdown", "-t", "json"], input=markdown, text=True
        ))
        nodes = []

        def visit(value):
            if isinstance(value, dict):
                if value.get("t") == "Math":
                    nodes.append((value["c"][0]["t"], value["c"][1].strip()))
                for child in value.values():
                    visit(child)
            elif isinstance(value, list):
                for child in value:
                    visit(child)

        visit(document["blocks"])
        return nodes

    def test_inline_and_display_math_survive_rendering(self):
        self.assertEqual(self.math_nodes(
            r"<p>\[ \sigma(\overline{W}x + b) \]</p>"
            r"<p>where \(n_1, \dots, n_k\) and \(b\).</p>"
        ), [
            ("DisplayMath", r"\sigma(\overline{W}x + b)"),
            ("InlineMath", r"n_1, \dots, n_k"),
            ("InlineMath", "b"),
        ])

    def test_blogger_breaks_entities_and_matrix_rows(self):
        self.assertEqual(self.math_nodes(
            r"<div>\[<br />W = \left[\begin{array}{cc}"
            r"x &amp; b\\0 &amp; 1\end{array}\right]<BR>\]</div>"
            r"<p>\(a_{l,n} \in \{0,1\}\)</p>"
        ), [
            ("DisplayMath", r"W = \left[\begin{array}{cc}x & b\\0 & 1\end{array}\right]"),
            ("InlineMath", r"a_{l,n} \in \{0,1\}"),
        ])

    def test_prose_code_and_video_are_preserved(self):
        iframe = '<iframe src="https://www.youtube.com/embed/example"></iframe>'
        markdown = convert_html_to_markdown(
            "pandoc", '<p>First<br>second <a href="https://example.com">link</a></p>'
            r'<pre><code>\(literal\)</code></pre>' + iframe
        )
        self.assertIn("First  \nsecond", markdown)
        self.assertIn("[link](https://example.com)", markdown)
        self.assertIn(r"\(literal\)", markdown)
        self.assertIn(iframe, markdown)
        self.assertIn("```{=html}", markdown)


if __name__ == "__main__":
    unittest.main()
