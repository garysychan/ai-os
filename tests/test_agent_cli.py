import io
import json
import unittest
from contextlib import redirect_stdout

from ai_os.cli import main


class AgentCliTests(unittest.TestCase):
    def run_cli(self, *args: str) -> tuple[int, str]:
        output = io.StringIO()
        with redirect_stdout(output):
            code = main(list(args))
        return code, output.getvalue()

    def test_agent_list_json_contains_all_roles(self) -> None:
        code, output = self.run_cli("agent", "list", "--json")
        payload = json.loads(output)
        self.assertEqual(code, 0)
        self.assertEqual(payload["status"], "PASS")
        self.assertEqual(len(payload["agents"]), 7)
        self.assertEqual(
            {item["role"] for item in payload["agents"]},
            {"Controller", "Planner", "Researcher", "Developer",
             "Tester", "Reviewer", "Fixer"},
        )

    def test_agent_describe_is_case_insensitive(self) -> None:
        code, output = self.run_cli(
            "agent", "describe", "developer", "--json"
        )
        payload = json.loads(output)
        self.assertEqual(code, 0)
        self.assertEqual(payload["role"], "Developer")
        self.assertIn("modify_code", payload["permissions"])

    def test_unknown_agent_role_fails(self) -> None:
        code, output = self.run_cli(
            "agent", "describe", "administrator", "--json"
        )
        payload = json.loads(output)
        self.assertEqual(code, 2)
        self.assertEqual(payload["status"], "FAIL")


if __name__ == "__main__":
    unittest.main()
