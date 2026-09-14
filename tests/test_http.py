import unittest

from app.common.http import make_session
from app.config.settings import USER_AGENT


class TestMakeSession(unittest.TestCase):
    def test_default_headers(self):
        session = make_session()
        self.assertEqual(session.headers["User-Agent"], USER_AGENT)
        self.assertEqual(session.headers["Accept"], "application/json")

    def test_custom_accept_header(self):
        session = make_session(accept="text/html")
        self.assertEqual(session.headers["Accept"], "text/html")

    def test_extra_headers_merged(self):
        session = make_session(extra_headers={"X-Custom": "value"})
        self.assertEqual(session.headers["X-Custom"], "value")
        self.assertEqual(session.headers["User-Agent"], USER_AGENT)

    def test_extra_headers_can_override_defaults(self):
        session = make_session(extra_headers={"Accept": "text/plain"})
        self.assertEqual(session.headers["Accept"], "text/plain")

    def test_each_call_returns_independent_session(self):
        session1 = make_session()
        session2 = make_session()
        session1.headers["X-Only-On-One"] = "yes"
        self.assertNotIn("X-Only-On-One", session2.headers)


if __name__ == "__main__":
    unittest.main()
