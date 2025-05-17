import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random
import os

# Step 1: Load existing dataset (correct path)
input_path = r'C:\Users\Ananyaaa\OneDrive\Desktop\AI_project\dataset_ai.csv'
if not os.path.exists(input_path):
    raise FileNotFoundError(f"File not found at {input_path}")

df = pd.read_csv(input_path)

# Step 2: Define parameters
TARGET_ROWS = 5000
TASK_TYPES = ['Analysis', 'Review', 'Meeting', 'Planning']
EMPLOYEE_IDS = list(range(101, 601))
START_DATE = datetime(2025, 4, 1)
END_DATE = datetime(2026, 4, 1)
TODAY = datetime(2025, 5, 12)  # Fixed reference date

# Step 3: Augmentation functions
def generate_task_name(task_type):
    subtypes = {
        'Analysis': ['Code Refactoring', 'API Optimization', 'Database Migration', 'Performance Tuning'],
        'Review': ['Experiment Design', 'Research Paper', 'Thesis Chapter', 'Documentation'],
        'Meeting': ['Sprint Planning', 'Retrospective', 'Client Call', 'Team Sync'],
        'Planning': ['Budget Report', 'Progress Review', 'Resource Allocation', 'Roadmap']
    }
    return f"{task_type} - {random.choice(subtypes[task_type])}"

def calculate_days_left(deadline_str):
    try:
        deadline = datetime.strptime(deadline_str, "%d-%m-%Y")
        return (deadline - TODAY).days
    except:
        return 0

def generate_dependencies(task_id):
    if task_id <= 1:
        return []
    return random.sample(range(1, task_id), k=random.randint(0, min(3, task_id-1)))

# Step 4: Generate new data
new_rows = []
for i in range(len(df)+1, TARGET_ROWS+1):
    task_type = random.choice(TASK_TYPES)
    deadline = (START_DATE + timedelta(days=random.randint(0, 365))).strftime("%d-%m-%Y")
    days_left = calculate_days_left(deadline)
    status = "Overdue" if days_left < 0 else random.choice(["Pending", "Pending", "Complete"])
    
    new_rows.append({
        'Task_ID': i,
        'Task_Name': generate_task_name(task_type),
        'Priority': random.randint(1,3),
        'Deadline': deadline,
        'Estimated_Time': random.randint(1,8),
        'Task_Type': task_type,
        'Dependency': generate_dependencies(i),
        'Employee_ID': random.choice(EMPLOYEE_IDS),
        'Completion_Status': "Complete" if status == "Complete" else "Incomplete",
        'Urgency_Score': random.randint(1,10),
        'Days_Left': abs(days_left),
        'Normalized_Urgency': round(random.uniform(0.1, 1.0), 1),
        'Dependency_Count': random.randint(0,3),
        'Status': status
    })

# Convert to DataFrame and merge
new_df = pd.DataFrame(new_rows)
df = pd.concat([df, new_df], ignore_index=True)

# Step 5: Post-processing
df['Normalized_Urgency'] = df['Urgency_Score'] / 10.0
df['Dependency'] = df['Dependency'].apply(lambda x: ','.join(map(str, x)) if isinstance(x, list) else '')
df = df.sample(frac=1).reset_index(drop=True)

# Step 6: Save
output_path = r'C:\Users\Ananyaaa\OneDrive\Desktop\AI_project\AI_5000.csv'
df.to_csv(output_path, index=False)
print(f"Dataset generated with {len(df)} entries. Saved to {output_path}")
