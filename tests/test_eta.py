import unittest

from app.common.eta import EtaEstimator, format_eta


class Clock:
    def __init__(self):
        self.t = 100.0

    def __call__(self):
        return self.t


class TestEta(unittest.TestCase):
    def setUp(self):
        self.clock = Clock()
        self.eta = EtaEstimator(window_seconds=20, clock=self.clock)

    def advance(self, seconds, done, total=1000):
        self.clock.t += seconds
        return self.eta.update(done, total)

    def test_no_estimate_until_enough_has_been_observed(self):
        self.assertIsNone(self.eta.update(0, 1000))
        self.assertIsNone(self.advance(1, 3))  # under 3 s of history

    def test_steady_rate(self):
        self.eta.update(0, 1000)
        for i in range(1, 10):
            remaining = self.advance(1, i * 3)  # 3 items per second
        self.assertAlmostEqual(remaining, (1000 - 27) / 3, delta=1)

    def test_an_initial_burst_does_not_make_the_rest_look_fast(self):
        self.eta.update(0, 1000)
        self.advance(0.1, 600)  # instant items: no network needed
        for i in range(1, 41):
            remaining = self.advance(1, 600 + i * 3)  # then 3 items/s
        # judged on the last 20 s only: 280 left at 3/s
        self.assertAlmostEqual(remaining, 280 / 3, delta=2)

    def test_nothing_to_show_when_done_stalled_or_nearly_over(self):
        self.eta.update(0, 100)
        self.assertIsNone(self.advance(10, 0, 100))  # stalled
        self.assertIsNone(self.advance(10, 99, 100))  # ~0.1 s left
        self.assertIsNone(self.advance(1, 100, 100))  # finished

    def test_format(self):
        self.assertEqual(format_eta(None), "")
        self.assertEqual(format_eta(7), "~5 s")
        self.assertEqual(format_eta(44), "~45 s")
        self.assertEqual(format_eta(61), "~2 min")
        self.assertEqual(format_eta(170), "~3 min")
        self.assertEqual(format_eta(3600 + 5 * 60 - 30), "~1 h 05 min")


if __name__ == "__main__":
    unittest.main()
