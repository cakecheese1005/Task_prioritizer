# train_model.py

import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report
import joblib
from datetime import datetime
import os

# ==================================================================
# CONFIGURATION - UPDATE THESE PATHS AS NEEDED
# ==================================================================
DATASET_PATH = r"C:\Users\Ananyaaa\OneDrive\Desktop\AI_project\AI_5000.csv"
MODEL_SAVE_PATH = r"C:\Users\Ananyaaa\OneDrive\Desktop\AI_project\task_priority_model.pkl"
FEATURES_SAVE_PATH = r"C:\Users\Ananyaaa\OneDrive\Desktop\AI_project\model_features.pkl"

# ==================================================================
# MODEL TRAINING PIPELINE
# ==================================================================

def main():
    # 1. Load dataset with path validation
    if not os.path.exists(DATASET_PATH):
        raise FileNotFoundError(f"Dataset not found at: {DATASET_PATH}")
        
    df = pd.read_csv(DATASET_PATH)

    # 2. Feature engineering
    current_date = datetime(2025, 5, 4)
    df['Deadline'] = pd.to_datetime(df['Deadline'], dayfirst=True)  # Handle DD-MM-YYYY format
    df['Days_Left'] = (df['Deadline'] - current_date).dt.days
    df['Status_Overdue'] = df['Status'].apply(lambda x: 1 if x == 'Overdue' else 0)

    # 3. Prepare features/target
    features = [
        'Urgency_Score',
        'Days_Left', 
        'Normalized_Urgency',
        'Dependency_Count',
        'Status_Overdue'
    ]
    
    X = df[features]
    y = df['Priority']

    # 4. Train/test split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, 
        test_size=0.2, 
        random_state=42,
        stratify=y
    )

    # 5. Model training
    model = RandomForestClassifier(
        n_estimators=150,  # Increased for larger dataset
        max_depth=7,
        random_state=42,
        class_weight='balanced'
    )
    model.fit(X_train, y_train)

    # 6. Evaluation
    y_pred = model.predict(X_test)
    print(f"\nModel Accuracy: {accuracy_score(y_test, y_pred):.2f}")
    print("Classification Report:\n", classification_report(y_test, y_pred))
    
    # 7. Save artifacts with full paths
    joblib.dump(model, MODEL_SAVE_PATH)
    joblib.dump(features, FEATURES_SAVE_PATH)
    
    print("\nTraining artifacts saved to:")
    print(f"- Model: {MODEL_SAVE_PATH}")
    print(f"- Features: {FEATURES_SAVE_PATH}")

if __name__ == "__main__":
    main()
