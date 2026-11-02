import os
import joblib


class HealthRiskPredictor:

    def __init__(self):

        base_dir = os.path.dirname(
            os.path.dirname(
                os.path.abspath(__file__)
            )
        )

        model_path = os.path.join(
            base_dir,
            "models",
            "health_model.pkl"
        )

        self.model = joblib.load(model_path)

        self.symptom_keys = [
            "fever",
            "cough",
            "fatigue",
            "shortness_of_breath",
            "chest_pain"
        ]


    def predict(self, symptoms):

        values = [
            int(symptoms.get(key, 0))
            for key in self.symptom_keys
        ]

        # Get prediction from trained ML model
        prediction = self.model.predict([values])[0]

        # Convert prediction to text
        risk_level = str(prediction)

        # Use risk level as the health status
        if risk_level == "Low":

            status = "Low Risk"

        elif risk_level == "Medium":

            status = "Needs Attention"

        elif risk_level == "High":

            status = "High Risk"

        else:

            status = risk_level


        return {
            "status": status,
            "risk_level": risk_level,
            "score": sum(values),
            "symptoms_checked": self.symptom_keys
        }