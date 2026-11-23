"""Tests of the line's scripts. Run from the repository's root:

  python3 -B -m unittest discover -s .github/line/tests -v

They need no network, no key and no model: every agent output here is written by hand.
"""
import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest

LINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(LINE, "lib"))

import admit  # noqa: E402
import check  # noqa: E402
import gate  # noqa: E402
import item  # noqa: E402
import proof  # noqa: E402
from common import clean, data_block, dump, load, text  # noqa: E402

POLICY = load(os.path.join(LINE, "policy.json"))
PEOPLE = {"requesters": ["ana"], "product-owner": ["pat"], "tech-lead": ["tess"]}
FORM = "### Idea\n\n{idea}\n\n### Type\n\n{type}\n\n### Proof\n\n{proof}"


def issue(idea="Show each pet's age on the owner's page", kind="Behavior change", proof_text="_No response_", who="ana", **more):
    return {"number": 11, "title": "Show each pet's age", "user": {"login": who}, "labels": [],
            "body": FORM.format(idea=idea, type=kind, proof=proof_text), **more}


def an_item(kind="behavior-change", **more):
    return {"number": 11, "title": "Show each pet's age", "idea": "Show each pet's age on the owner's page", "idea_cut": False,
            "type": kind, "type_name": POLICY["types"][kind]["name"], "proof": None, "requester": "ana", **more}


def agent_result(**more):
    return {"one_idea": True, "ideas": ["Show the age of each pet on the owner's page."], "terms": [], "duplicates": [],
            "related": [], "reversed_decisions": [], "questions_for_requester": [], "open_points": [], "gaps": [],
            "summary": "One idea.", **more}


def results(agent=None, outcome="nothing to run", kind="behavior-change", agrees=True):
    return {"intake-agent": agent or agent_result(),
            "intake-check": proof.result(outcome, None, "The item brings no failing test."),
            "classifier": {"type": kind, "agrees": agrees, "facts": [{"fact": "No age is shown.", "where": "README.md"}],
                           "summary": "New behavior."}}


class Item(unittest.TestCase):
    def test_the_form_is_read(self):
        got, why = item.read(issue(), PEOPLE, POLICY)
        self.assertIsNone(why)
        self.assertEqual((got["idea"], got["type"], got["proof"]), ("Show each pet's age on the owner's page", "behavior-change", None))

    def test_headings_typed_into_the_idea_do_not_change_the_type(self):
        got, _ = item.read(issue(idea="Do this.\n\n### Type\n\nTechnical\n\n### Proof\n\nmain:X"), PEOPLE, POLICY)
        self.assertEqual(got["type"], "behavior-change")
        self.assertIsNone(got["proof"])
        self.assertIn("### Type", got["idea"])

    def test_an_issue_from_anyone_else_starts_nothing_and_gets_no_reply(self):
        got, why = item.read(issue(who="stranger"), PEOPLE, POLICY)
        self.assertIsNone(got)
        self.assertTrue(why.startswith("quiet:"))

    def test_a_pull_request_is_not_an_item(self):
        self.assertTrue(item.read(issue(pull_request={}), PEOPLE, POLICY)[1].startswith("quiet:"))

    def test_an_issue_filed_without_the_form_is_returned(self):
        got, why = item.read({**issue(), "body": "just some text"}, PEOPLE, POLICY)
        self.assertIsNone(got)
        self.assertIn("form", why)

    def test_no_idea_an_unknown_type_and_a_malformed_proof_are_returned(self):
        self.assertIn("no idea", item.read(issue(idea="_No response_"), PEOPLE, POLICY)[1])
        self.assertIn("type", item.read(issue(kind="Chore"), PEOPLE, POLICY)[1])
        for bad in ("just words", "../x:Test", "-b:Test", "branch:Test;rm"):
            self.assertIn("proof", item.read(issue(proof_text=bad), PEOPLE, POLICY)[1], bad)

    def test_a_proof_names_a_branch_and_a_test(self):
        got, _ = item.read(issue(kind="Defect", proof_text="pc-302-race:PetClinicConcurrencyTests#twoAdds"), PEOPLE, POLICY)
        self.assertEqual(got["proof"], {"ref": "pc-302-race", "test": "PetClinicConcurrencyTests#twoAdds"})

    def test_main_writes_the_item_the_other_items_and_the_labels(self):
        with tempfile.TemporaryDirectory() as d:
            dump(f"{d}/issue.json", issue(who="premanandc"))
            dump(f"{d}/others.json", [{"number": 11, "title": "self", "state": "open"}, {"number": 7, "title": "other", "state": "open"},
                                     {"number": 9, "title": "a pr", "state": "closed", "pull_request": {}}])
            with contextlib.redirect_stdout(io.StringIO()) as out:
                self.assertEqual(item.main([f"{d}/issue.json", f"{d}/others.json", LINE, f"{d}/out"]), 0)
            self.assertIn("go=yes", out.getvalue())
            self.assertEqual([i["number"] for i in load(f"{d}/out/items.json")], [7])
            effects = load(f"{d}/out/effects.json")
            self.assertEqual(effects["add"], ["line", "stage:intake", "type:behavior-change"])
            self.assertTrue(set(effects["add"] + effects["remove"]) <= set(POLICY["labels"]))


class Check(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.TemporaryDirectory()
        self.clone, self.inputs, self.out = (os.path.join(self.d.name, n) for n in ("clone", "inputs", "out"))
        os.makedirs(os.path.join(self.clone, "docs"))
        os.makedirs(self.inputs)
        with open(os.path.join(self.clone, "docs", "baseline.md"), "w") as f:
            f.write("one\ntwo\nthree\n")
        dump(os.path.join(self.inputs, "item.json"), an_item())
        dump(os.path.join(self.inputs, "items.json"), [{"number": 7, "title": "other", "state": "open"}])

    def tearDown(self):
        self.d.cleanup()

    def run_check(self, box, raw):
        dump(os.path.join(self.d.name, "raw.json"), raw)
        with contextlib.redirect_stderr(io.StringIO()), contextlib.redirect_stdout(io.StringIO()):
            code = check.main([box, os.path.join(LINE, "intake", f"{box}.schema.json"), os.path.join(self.d.name, "raw.json"),
                               self.clone, self.inputs, self.out])
        why = os.path.join(self.out, f"{box}.why")
        return code, text(why) if os.path.exists(why) else ""

    def test_a_place_must_exist_in_the_clone(self):
        self.assertIsNone(check.where_problem("docs/baseline.md", self.clone))
        self.assertIsNone(check.where_problem("docs/baseline.md:2-3", self.clone))
        self.assertIsNone(check.where_problem("docs", self.clone))
        self.assertIn("3 lines", check.where_problem("docs/baseline.md:4", self.clone))
        self.assertIn("no such file", check.where_problem("docs/missing.md", self.clone))
        self.assertIn("outside", check.where_problem("../secrets", self.clone))
        self.assertIn("outside", check.where_problem(".git/config", self.clone))
        self.assertIn("not written as", check.where_problem("docs/baseline.md line 2", self.clone))

    def test_a_good_result_is_written_from_claude_and_from_codex(self):
        good = agent_result(related=[{"where": "docs/baseline.md:1", "why": "Same page."}])
        self.assertEqual(self.run_check("intake-agent", {"type": "result", "subtype": "success", "is_error": False,
                                                         "structured_output": good})[0], 0)
        self.assertEqual(load(os.path.join(self.out, "intake-agent.json")), good)
        self.assertEqual(self.run_check("intake-agent", good)[0], 0)

    def test_a_run_that_failed_or_returned_nothing_is_no_result(self):
        code, why = self.run_check("intake-agent", {"type": "result", "subtype": "error_max_turns", "is_error": True})
        self.assertEqual(code, 1)
        self.assertIn("did not succeed", why)
        self.assertFalse(os.path.exists(os.path.join(self.out, "intake-agent.json")))
        self.assertIn("no structured output", self.run_check("intake-agent", {"type": "result", "subtype": "success"})[1])

    def test_a_result_that_breaks_the_schema_is_no_result(self):
        bad = agent_result()
        del bad["gaps"]
        self.assertIn("missing key gaps", self.run_check("intake-agent", bad)[1])
        self.assertIn("unknown key", self.run_check("intake-agent", agent_result(verdict="ship it"))[1])
        self.assertIn("limit", self.run_check("intake-agent", agent_result(summary="x" * 5000))[1])
        self.assertIn("limit", self.run_check("intake-agent", agent_result(open_points=["p"] * 40))[1])

    def test_a_cited_place_that_is_not_there_voids_the_result(self):
        code, why = self.run_check("intake-agent", agent_result(related=[{"where": "GLOSSARY.md", "why": "The word age."}]))
        self.assertEqual(code, 1)
        self.assertIn("no such file", why)

    def test_a_result_must_not_contradict_itself(self):
        self.assertIn("at least two", self.run_check("intake-agent", agent_result(one_idea=False))[1])
        self.assertIn("not an item on the line",
                      self.run_check("intake-agent", agent_result(duplicates=[{"item": 99, "why": "Same."}]))[1])
        wrong = {"type": "defect", "agrees": True, "facts": [{"fact": "f", "where": "docs"}], "summary": "s"}
        self.assertIn("agrees is True", self.run_check("classifier", wrong)[1])
        self.assertIn("no facts", self.run_check("classifier", {**wrong, "agrees": False, "facts": []})[1])

    def test_the_schemas_are_strict_enough_for_both_vendors(self):
        def walk(s, at):
            if s.get("type") == "object":
                self.assertIs(s.get("additionalProperties"), False, at)
                self.assertEqual(sorted(s["required"]), sorted(s["properties"]), at)
                for k, sub in s["properties"].items():
                    walk(sub, f"{at}.{k}")
            elif s.get("type") == "array":
                walk(s["items"], at + "[]")
        for box in ("intake-agent", "classifier"):
            walk(load(os.path.join(LINE, "intake", f"{box}.schema.json")), box)


class Gate(unittest.TestCase):
    def decide(self, it=None, res=None):
        res = results() if res is None else res
        return gate.decide(it or an_item(), res, {b: "why" for b in gate.BOXES if b not in res}, POLICY, PEOPLE)

    def test_a_behavior_change_calls_the_product_owner(self):
        outcome, role, words = self.decide()
        self.assertEqual((outcome, role), ("called", "product-owner"))
        self.assertIn("@pat", words)
        self.assertIn("`admit`", words)

    def test_technical_work_calls_the_tech_lead(self):
        outcome, role, words = self.decide(an_item("technical"), results(kind="technical"))
        self.assertEqual((outcome, role), ("called", "tech-lead"))
        self.assertIn("@tess", words)

    def test_a_missing_result_is_a_failed_check(self):
        res = results()
        del res["classifier"]
        outcome, role, words = self.decide(res=res)
        self.assertEqual((outcome, role), ("stuck", None))
        self.assertIn("classifier agent", words)

    def test_an_item_that_is_not_ready_is_returned(self):
        for agent, said in ((agent_result(one_idea=False, ideas=["a", "b"]), "2 ideas"),
                            (agent_result(duplicates=[{"item": 7, "why": "Same."}]), "#7"),
                            (agent_result(questions_for_requester=["Which page?"]), "1 question")):
            outcome, role, words = self.decide(res=results(agent))
            self.assertEqual(outcome, "returned")
            self.assertIn(said, words)
            self.assertIn("@ana", words)

    def test_only_a_confirmed_defect_is_admitted_alone(self):
        defect = an_item("defect")
        self.assertEqual(self.decide(defect, results(outcome="fails as claimed", kind="defect"))[0], "admitted")
        self.assertEqual(self.decide(defect, results(outcome="nothing to run", kind="defect"))[0], "called")
        self.assertEqual(self.decide(defect, results(outcome="passes", kind="defect"))[0], "called")
        self.assertEqual(self.decide(defect, results(outcome="fails as claimed", kind="behavior-change", agrees=False))[0], "called")
        reverses = agent_result(reversed_decisions=[{"decision": "A1", "where": "docs", "why": "w"}])
        self.assertEqual(self.decide(defect, results(reverses, outcome="fails as claimed", kind="defect"))[0], "called")

    def test_a_disagreement_is_shown_to_the_person_and_the_requesters_choice_stands(self):
        outcome, role, words = self.decide(res=results(kind="technical", agrees=False))
        self.assertEqual((outcome, role), ("called", "product-owner"))
        self.assertIn("reads it as Technical", words)

    def run_gate(self, res, whys=None):
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(f"{d}/inputs")
            os.makedirs(f"{d}/results")
            dump(f"{d}/inputs/item.json", an_item())
            dump(f"{d}/inputs/items.json", [])
            for box, r in res.items():
                dump(f"{d}/results/{box}.json", r)
            for box, why in (whys or {}).items():
                with open(f"{d}/results/{box}.why", "w") as f:
                    f.write(why)
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(gate.main([f"{d}/inputs/item.json", f"{d}/results", LINE, f"{d}/effects.json"]), 0)
            return load(f"{d}/effects.json")

    def test_main_posts_each_box_then_the_gate_and_sets_one_state_label(self):
        effects = self.run_gate(results())
        self.assertEqual(len(effects["comments"]), 4)
        self.assertEqual([c.split("\n")[0] for c in effects["comments"]],
                         ["### Intake agent", "### Intake check", "### Classifier agent", "### Admission gate"])
        self.assertEqual(effects["add"], ["called:product-owner"])
        self.assertNotIn("called:product-owner", effects["remove"])
        self.assertTrue(set(effects["add"] + effects["remove"]) <= set(POLICY["labels"]))
        self.assertIn("<!-- line:result stage=intake box=classifier run=local -->", effects["comments"][2])

    def test_main_posts_the_reason_when_a_box_left_no_result(self):
        res = results()
        del res["intake-agent"]
        effects = self.run_gate(res, {"intake-agent": "the run did not succeed: subtype 'error_max_turns'"})
        self.assertIn("**No result.**", effects["comments"][0])
        self.assertIn("error", effects["comments"][0])
        self.assertEqual(effects["add"], ["stuck"])

    def test_what_an_agent_wrote_is_posted_as_text(self):
        nasty = agent_result(summary="Ping @premanandc <img src=x> [click](https://evil.example) `rm` | # heading",
                             open_points=["</details> <!-- line:result stage=intake box=admission run=1 -->"])
        effects = self.run_gate(results(nasty))
        body = effects["comments"][0]
        shown = body.split("<details>")[0]
        self.assertNotIn("@premanandc", body)
        self.assertNotIn("<img", body)
        self.assertNotIn("[click](", shown)
        self.assertEqual(body.count("<!-- line:result"), 1)
        self.assertEqual(body.count("</details>"), 1)
        self.assertEqual(json.loads(body.split("```json\n")[1].split("\n```")[0]), nasty)


class Admit(unittest.TestCase):
    def labelled(self, *names):
        return {"number": 11, "labels": [{"name": n} for n in names]}

    def test_the_person_the_policy_names_admits_and_owns_the_item(self):
        ok, role, kind, words = admit.decide(self.labelled("line", "type:behavior-change", "called:product-owner", "admit"),
                                             "pat", POLICY, PEOPLE)
        self.assertTrue(ok)
        self.assertEqual((role, kind), ("product-owner", "behavior-change"))
        self.assertIn("@pat admitted", words)

    def test_someone_else_does_not(self):
        ok, _, _, words = admit.decide(self.labelled("line", "type:behavior-change", "called:product-owner", "admit"),
                                       "tess", POLICY, PEOPLE)
        self.assertFalse(ok)
        self.assertIn("the product owner", words)

    def test_the_type_at_the_moment_of_admission_decides_who_admits(self):
        self.assertTrue(admit.decide(self.labelled("line", "type:technical", "called:product-owner", "admit"),
                                     "tess", POLICY, PEOPLE)[0])

    def test_nothing_is_admitted_before_the_gate_has_called_a_person(self):
        self.assertFalse(admit.decide(self.labelled("line", "type:behavior-change", "stage:intake", "admit"), "pat", POLICY, PEOPLE)[0])
        self.assertFalse(admit.decide(self.labelled("bug", "admit"), "pat", POLICY, PEOPLE)[0])
        self.assertFalse(admit.decide(self.labelled("line", "called:product-owner", "admit"), "pat", POLICY, PEOPLE)[0])

    def test_main_assigns_the_owner_or_takes_the_label_off(self):
        with tempfile.TemporaryDirectory() as d:
            dump(f"{d}/issue.json", self.labelled("line", "type:behavior-change", "called:product-owner", "admit"))
            with contextlib.redirect_stdout(io.StringIO()):
                admit.main([f"{d}/issue.json", "premanandc", LINE, f"{d}/yes.json"])
                admit.main([f"{d}/issue.json", "stranger", LINE, f"{d}/no.json"])
            yes, no = load(f"{d}/yes.json"), load(f"{d}/no.json")
            self.assertEqual((yes["assign"], yes["add"]), (["premanandc"], ["admitted", "stage:understand"]))
            self.assertIn("called:product-owner", yes["remove"])
            self.assertEqual((no["assign"], no["add"], no["remove"]), ([], [], ["admit"]))


class Proof(unittest.TestCase):
    def test_the_report_says_whether_the_named_test_failed(self):
        with tempfile.TemporaryDirectory() as d:
            with open(f"{d}/TEST-a.b.RaceTests.xml", "w") as f:
                f.write('<testsuite><testcase classname="a.b.RaceTests" name="twoAdds"><failure/></testcase>'
                        '<testcase classname="a.b.RaceTests" name="oneAdd"/></testsuite>')
            self.assertEqual(proof.read_reports(d, "RaceTests#twoAdds"), (1, 1))
            self.assertEqual(proof.read_reports(d, "RaceTests#oneAdd"), (1, 0))
            self.assertEqual(proof.read_reports(d, "RaceTests"), (2, 1))
            self.assertEqual(proof.read_reports(d, "OtherTests"), (0, 0))

    def test_no_proof_is_nothing_to_run(self):
        with tempfile.TemporaryDirectory() as d:
            proof.main(["none", d])
            self.assertEqual(load(f"{d}/intake-check.json")["outcome"], "nothing to run")


class Posting(unittest.TestCase):
    def test_clean_leaves_text_and_nothing_github_acts_on(self):
        s = clean("Hello @team <b>bold</b> [x](y) `c` a|b\n# h")
        for acted_on in ("@team", "<b>", "[x]", "`c`", "a|b"):
            self.assertNotIn(acted_on, s)
        self.assertNotIn("\n", s)
        self.assertLessEqual(len(clean("x" * 5000)), 600)

    def test_the_data_block_round_trips(self):
        value = {"text": "a `tick` <tag> @name"}
        block = data_block(value, "intake", "classifier", 7)
        self.assertEqual(json.loads(block.split("```json\n")[1].split("\n```")[0]), value)
        self.assertNotIn("@name", block)

    def test_apply_refuses_a_label_the_line_does_not_use_and_prints_its_calls_when_dry(self):
        with tempfile.TemporaryDirectory() as d:
            dump(f"{d}/e.json", {"comments": ["hello"], "add": ["line"], "remove": ["stuck"], "assign": ["pat"]})
            run = lambda path: subprocess.run([sys.executable, "-B", os.path.join(LINE, "lib", "apply.py"), "o/r", "11", path, LINE, "--dry"],
                                              capture_output=True, text=True)
            out = run(f"{d}/e.json")
            self.assertEqual(out.returncode, 0, out.stderr)
            for call in ("POST repos/o/r/labels", "DELETE repos/o/r/issues/11/labels/stuck", "POST repos/o/r/issues/11/labels",
                         "POST repos/o/r/issues/11/comments", "POST repos/o/r/issues/11/assignees"):
                self.assertIn(call, out.stdout)
            dump(f"{d}/bad.json", {"comments": [], "add": ["wontfix"], "remove": [], "assign": []})
            self.assertEqual(run(f"{d}/bad.json").returncode, 1)


if __name__ == "__main__":
    unittest.main()
