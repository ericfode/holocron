"""Read-only source/catalog contract checks; no Cargo/native/model execution."""
import json
from pathlib import Path
import re
import unittest

HERE=Path(__file__).resolve().parent


class PublicTraitInputTests(unittest.TestCase):
    def test_source_reads_actual_definition_code_from_public_pinned_rows(self):
        source=(HERE/"src/main.rs").read_text()
        lookup=source.split("fn public_printed_has_trait",1)[1].split("fn other_fighter_count",1)[0]
        count=source.split("fn other_fighter_count",1)[1].split("fn capture",1)[0]
        self.assertIn('plan.get("selected_whole_rows").and_then(|v|v.get(code))',lookup)
        self.assertIn('row.get("card").and_then(|v|v.get("traits"))',lookup)
        self.assertNotIn("&Engine",lookup);self.assertNotIn("&State",lookup)
        self.assertIn('e.definitions[s.card(id).def as usize].code.as_str()',count)
        self.assertIn('if id==refs[0]{continue;}',count)
        self.assertNotIn('.info.traits',source)
        self.assertNotIn('.definitions[s.card(id).def as usize].traits',source)
        for call in re.findall(r'capture\(([^\n]*?)\)\?',source):
            self.assertTrue(call.endswith(',plan'),call)

    def test_all_current_complete_rows_have_printed_traits_without_trait_changes(self):
        plan=json.loads((HERE/"collection-plan.json").read_text())
        rows=plan["selected_whole_rows"]
        def kinds(value):
            if isinstance(value,dict):
                yield value.get("kind")
                for child in value.values():yield from kinds(child)
            elif isinstance(value,list):
                for child in value:yield from kinds(child)
        for code,row in rows.items():
            with self.subTest(code=code):
                self.assertIsInstance(row["card"]["traits"],list)
                self.assertTrue(all(isinstance(x,str) for x in row["card"]["traits"]))
                self.assertFalse({"gainTrait","loseTrait"}&set(kinds(row)))
        self.assertIn("fighter",rows[plan["helpers"]["other_fighter"]]["card"]["traits"])
        self.assertNotIn("fighter",rows[plan["helpers"]["other_nonfighter"]]["card"]["traits"])
        # Both entering space sources are Fighters: excluding the source matters.
        for code in ("JTL_158","JTL_217"):
            self.assertIn("fighter",rows[code]["card"]["traits"])


if __name__=="__main__":unittest.main()
