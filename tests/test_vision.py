import unittest
from unittest.mock import Mock, patch

from modules import vision


class CloudflareVisionTests(unittest.TestCase):
    @patch("modules.vision.requests.post")
    def test_call_cloudflare_vision_returns_response_text_on_success(self, post):
        vision.cloudflare_ready = True
        vision.CLOUDFLARE_ACCOUNT_ID = "account-123"

        response = Mock(status_code=200)
        response.json.return_value = {"result": {"response": "screen looks clear"}}
        post.return_value = response

        result = vision._call_cloudflare_vision("Describe this image", "abcd1234")

        self.assertEqual(result, "screen looks clear")
        self.assertEqual(post.call_count, 2)

    @patch("modules.vision.requests.post")
    def test_call_cloudflare_vision_returns_none_for_agreement_error(self, post):
        vision.cloudflare_ready = True
        vision.CLOUDFLARE_ACCOUNT_ID = "account-123"

        response = Mock(status_code=403)
        response.text = "Model Agreement required"
        post.return_value = response

        result = vision._call_cloudflare_vision("Describe this image", "abcd1234")

        self.assertIsNone(result)
        self.assertEqual(post.call_count, 2)


if __name__ == "__main__":
    unittest.main()
