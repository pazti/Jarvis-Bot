import unittest
import modules.actions as actions
from modules.memory import get_memory_summary
import os
import tempfile

class NoteTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "test_memory.db")
        self.callbacks = {
            "response": lambda msg: None,
            "status": lambda msg: None,
            "processing": lambda val: None,
            "skip_audio": lambda val: None,
        }

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_quick_note_persists_in_memory(self):
        note_text = "Remember to buy milk tomorrow"
        prompt = f"create a quick note: {note_text}"
        
        # Action should return a success message. 
        # We must pass db_path because the action now supports it.
        result = actions.quick_note_action(prompt, self.callbacks, db_path=self.db_path)
        self.assertIn("Quick note saved", result)
        
        # Verify the note is actually in the memory DB
        summary = get_memory_summary(db_path=self.db_path, category="general")
        self.assertIn(note_text, summary)

if __name__ == "__main__":
    unittest.main()
