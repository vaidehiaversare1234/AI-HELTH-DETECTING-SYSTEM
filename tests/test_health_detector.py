import unittest

from src.health_detector import HealthRiskPredictor


class TestHealthRiskPredictor(unittest.TestCase):
    def test_healthy_prediction(self):
        predictor = HealthRiskPredictor()
        result = predictor.predict(
            {
                "fever": 0,
                "cough": 0,
                "fatigue": 0,
                "shortness_of_breath": 0,
                "chest_pain": 0,
            }
        )
        self.assertEqual(result["status"], "Healthy")

    def test_high_risk_prediction(self):
        predictor = HealthRiskPredictor()
        result = predictor.predict(
            {
                "fever": 1,
                "cough": 1,
                "fatigue": 1,
                "shortness_of_breath": 1,
                "chest_pain": 1,
            }
        )
        self.assertIn(result["status"], ["Needs Attention", "Emergency"])


if __name__ == "__main__":
    unittest.main()
