import os
import pandas as pd

from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score

import joblib


# -----------------------------------------
# 1. Project folders
# -----------------------------------------

DATASET_PATH = "dataset/health_data.csv"
MODEL_PATH = "models/health_model.pkl"


# -----------------------------------------
# 2. Check whether dataset exists
# -----------------------------------------

if not os.path.exists(DATASET_PATH):

    print("ERROR: Dataset not found.")
    print("Please create:")
    print(DATASET_PATH)

    exit()


# -----------------------------------------
# 3. Load dataset
# -----------------------------------------

data = pd.read_csv(DATASET_PATH)

print("Dataset loaded successfully.")
print("Number of records:", len(data))


# -----------------------------------------
# 4. Select input symptoms
# -----------------------------------------

features = [
    "fever",
    "cough",
    "fatigue",
    "shortness_of_breath",
    "chest_pain"
]


X = data[features]

y = data["risk_level"]


# -----------------------------------------
# 5. Split dataset
# -----------------------------------------

X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.2,
    random_state=42,
    stratify=y
)


# -----------------------------------------
# 6. Create ML model
# -----------------------------------------

model = RandomForestClassifier(
    n_estimators=100,
    random_state=42
)


# -----------------------------------------
# 7. Train model
# -----------------------------------------

print("Training machine-learning model...")

model.fit(X_train, y_train)


# -----------------------------------------
# 8. Test model
# -----------------------------------------

predictions = model.predict(X_test)

accuracy = accuracy_score(
    y_test,
    predictions
)


print("Model training completed.")
print("Model accuracy:", round(accuracy * 100, 2), "%")


# -----------------------------------------
# 9. Create models folder
# -----------------------------------------

os.makedirs(
    "models",
    exist_ok=True
)


# -----------------------------------------
# 10. Save trained model
# -----------------------------------------

joblib.dump(
    model,
    MODEL_PATH
)


print()
print("Model saved successfully!")
print("Location:", MODEL_PATH)