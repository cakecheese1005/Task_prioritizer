from datetime import datetime
from typing import List, Dict
import joblib
import logging  # Import the logging module

# Get a logger for this module
logger = logging.getLogger(__name__)

# --- MODEL LOADING ---
MODEL_LOAD_FAILED = False  # Initialize the flag

try:
    model = joblib.load('task_priority_model.pkl')
    features = joblib.load('model_features.pkl')
    logger.info("Model and features loaded successfully.")
except FileNotFoundError as e:
    MODEL_LOAD_FAILED = True
    model = None
    features = []
    logger.error(f"Model loading failed (FileNotFoundError): {e}")
except Exception as e:
    MODEL_LOAD_FAILED = True
    model = None
    features = []
    logger.exception(f"Unexpected error during model loading: {e}")


# --- FEATURE EXTRACTION ---
def extract_features(task: Dict, current_time: datetime) -> List[float]:
    """Extracts features from a task dictionary."""
    days_left = None  # Initialize to None
    try:
        deadline = datetime.strptime(task['deadline'], "%Y-%m-%d")
        days_left = (deadline - current_time).days
    except ValueError as e:
        logger.error(f"Invalid deadline for task {task.get('id', 'unknown')}: {e}")
        days_left = 9999  # Or float('inf') - but be consistent
    except TypeError as e:
        logger.error(f"TypeError processing deadline for task {task.get('id', 'unknown')}: {e}")
        days_left = 9999
    except Exception as e:
        logger.exception(f"Error extracting deadline for task {task.get('id', 'unknown')}: {e}")
        days_left = 9999

    extracted_features = [
        days_left if days_left is not None else 9999,  # Handle potential None
        task.get('urgency_score', 0),
        len(task.get('dependencies', [])),
        task.get('normalized_urgency', 0.0),
        1 if task.get('status', '').lower() == 'overdue' else 0,
    ]

    logger.debug(f"Extracted features for task {task.get('id', 'unknown')}: {extracted_features}")
    return extracted_features


# --- FEATURE VALIDATION ---
def validate_features(features: List[float]) -> bool:
    """Validates the extracted features."""
    if not isinstance(features, list) or len(features) != 5:
        logger.error(f"Invalid feature format: {features}")
        return False
    for f in features:
        if not isinstance(f, (int, float)):
            logger.error(f"Invalid feature type: {features}")
            return False
    return True


# --- PREDICTION ---
def predict_task_priority(task: Dict, current_time: datetime) -> float:
    """Predicts task priority using the loaded model."""
    if MODEL_LOAD_FAILED or model is None:
        logger.error("predict_task_priority called but model is not loaded.")
        raise ValueError("Model not loaded.")

    task_features = extract_features(task, current_time)
    if not validate_features(task_features):
        logger.error(f"Invalid features for task {task.get('id', 'unknown')}: {task_features}")
        raise ValueError("Invalid features.")

    try:
        prediction = float(model.predict([task_features])[0])
        logger.debug(f"Prediction for task {task.get('id', 'unknown')}: {prediction}")
        return prediction
    except Exception as e:
        logger.exception(f"Error predicting priority for task {task.get('id', 'unknown')}: {e}")
        raise  # Re-raise


# --- DEPENDENCY CHECK ---
def dependencies_met(task: Dict, completed_ids: List[int]) -> bool:
    """Checks if all dependencies for a task are met."""
    return all(dep in completed_ids for dep in task.get('dependencies', []))


# --- TASK PRIORITIZATION ---
def prioritize_tasks(task_list: List[Dict], completed_ids: List[int] = []) -> List[Dict]:
    """Prioritizes tasks based on ML and dependencies."""

    current_time = datetime.now()
    prioritized_tasks = []

    for task in task_list:
        task_id = task.get('id', 'unknown')
        try:
            if dependencies_met(task, completed_ids):
                task['score'] = predict_task_priority(task, current_time)
                task['status'] = 'Ready'
            else:
                task['score'] = -1
                task['status'] = 'Blocked'
            prioritized_tasks.append(task)  # Append task to the new list
        except ValueError as ve:
            logger.error(f"ValueError prioritizing task {task_id}: {ve}")
            task['score'] = -2
            task['status'] = 'Error'
            task['error'] = str(ve)
            prioritized_tasks.append(task)
        except Exception as e:
            logger.exception(f"Unexpected error prioritizing task {task_id}: {e}")
            task['score'] = -2
            task['status'] = 'Error'
            task['error'] = str(e)
            prioritized_tasks.append(task)

    ready_tasks = [t for t in prioritized_tasks if t['status'] == 'Ready']
    blocked_error_tasks = [t for t in prioritized_tasks if t['status'] in ('Blocked', 'Error')]

    ready_tasks.sort(key=lambda x: x['score'], reverse=True)
    return ready_tasks + blocked_error_tasks
       