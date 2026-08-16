import os
import tempfile
import unittest

from modules.memory import (
    build_memory_context,
    extract_fact_from_prompt,
    forget_memory,
    get_facts,
    get_memory_summary,
    get_recent_conversation,
    init_memory_db,
    remember_memory,
    save_fact,
    save_message,
    trim_conversation_for_summary,
)


class MemoryTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "jarvis_memory.db")
        init_memory_db(self.db_path)

    def test_save_and_read_recent_conversation(self):
        save_message("user", "hello jarvis")
        save_message("assistant", "hello sir")

        messages = get_recent_conversation(db_path=self.db_path, limit=10)

        self.assertEqual(len(messages), 2)
        self.assertEqual(messages[0]["role"], "user")
        self.assertEqual(messages[1]["role"], "assistant")

    def test_save_and_get_fact(self):
        save_fact("name", "Paul", "identity", db_path=self.db_path)
        facts = get_facts(db_path=self.db_path)

        self.assertEqual(len(facts), 1)
        self.assertEqual(facts[0]["key"], "name")
        self.assertEqual(facts[0]["value"], "Paul")

    def test_build_memory_context_uses_recent_and_facts(self):
        save_message("user", "I like python")
        save_message("assistant", "Great, I can help with Python")
        save_fact("favorite_language", "Python", "preference", db_path=self.db_path)

        context = build_memory_context(db_path=self.db_path, recent_limit=5, fact_limit=5)

        self.assertIn("Recent conversation", context)
        self.assertIn("favorite_language", context)
        self.assertIn("Python", context)

    def test_remember_command_saves_fact(self):
        result = remember_memory("remember this: I prefer short answers", db_path=self.db_path)

        self.assertTrue(result)
        facts = get_facts(db_path=self.db_path)
        self.assertTrue(any(f["key"] == "user_note" for f in facts))

    def test_forget_command_removes_fact(self):
        save_fact("favorite_language", "Python", "preference", db_path=self.db_path)

        result = forget_memory("forget that favorite language", db_path=self.db_path)

        self.assertTrue(result)
        self.assertEqual(len(get_facts(db_path=self.db_path)), 0)

    def test_extract_fact_from_prompt(self):
        fact = extract_fact_from_prompt("my favorite language is Python", db_path=self.db_path)

        self.assertIsNotNone(fact)
        self.assertEqual(fact["key"], "favorite_language")
        self.assertEqual(fact["value"], "Python")

    def test_trim_conversation_for_summary(self):
        for index in range(1, 16):
            save_message("user", f"message {index}", db_path=self.db_path)

        summary = trim_conversation_for_summary(db_path=self.db_path, max_messages=10)

        self.assertIn("message", summary.lower())
        self.assertLessEqual(len(get_recent_conversation(db_path=self.db_path, limit=20)), 10)

    def test_memory_categories_and_show_summary(self):
        save_fact("work_note", "I prefer Python for backend work", "work", db_path=self.db_path)
        save_fact("personal_note", "I like calm and focused environments", "personal", db_path=self.db_path)
        save_fact("developer_preferences", "I like fast, clean APIs", "developer_preferences", db_path=self.db_path)

        work_summary = get_memory_summary(db_path=self.db_path, category="work")
        personal_summary = get_memory_summary(db_path=self.db_path, category="personal")

        self.assertIn("Python", work_summary)
        self.assertIn("calm", personal_summary.lower())

    def test_show_my_memory_command_category(self):
        save_fact("developer_preferences", "I prefer Python and async systems", "developer_preferences", db_path=self.db_path)
        fact = extract_fact_from_prompt("show my developer memory", db_path=self.db_path)

        self.assertIsNone(fact)
        self.assertIn("Python", get_memory_summary(db_path=self.db_path, category="developer_preferences"))

    def test_forget_memory_by_category_and_value(self):
        save_fact("developer_preferences", "I prefer Python and async systems", "developer_preferences", db_path=self.db_path)
        save_fact("work_note", "Focus on automation and AI workflows", "work", db_path=self.db_path)

        result = forget_memory("forget my developer preferences", db_path=self.db_path)

        self.assertTrue(result)
        self.assertEqual(len(get_facts(db_path=self.db_path, category="developer_preferences")), 0)


if __name__ == "__main__":
    unittest.main()
