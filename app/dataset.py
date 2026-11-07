# dataset.py
import json
import random
from pathlib import Path

# Determine project root dynamically (assumes dataset.py is in project root or app/)
CURRENT_DIR = Path(__file__).resolve().parent
if CURRENT_DIR.name == "app":
    PROJECT_ROOT = CURRENT_DIR.parent
else:
    PROJECT_ROOT = CURRENT_DIR

# Set path to project root/data/loans.json
DATA_DIR = PROJECT_ROOT / "data"
DATA_FILE = DATA_DIR / "loans.json"
SEED = 42

CATEGORIES = [
    "Personal Loan", 
    "Home Loan", 
    "Auto Loan", 
    "Education Loan", 
    "Business Loan"
]

STATUSES = [
    "Submitted", 
    "Under Review", 
    "Approved", 
    "Rejected", 
    "Disbursed"
]

def get_realistic_loan_amount(category: str) -> int:
    """Returns a realistic loan amount in INR based on the loan category."""
    ranges = {
        "Personal Loan": (50000, 1000000),      # ₹50K - ₹10L
        "Education Loan": (100000, 2500000),    # ₹1L - ₹25L
        "Auto Loan": (300000, 2000000),         # ₹3L - ₹20L
        "Home Loan": (1500000, 5000000),        # ₹15L - ₹50L
        "Business Loan": (500000, 5000000)      # ₹5L - ₹50L
    }
    low, high = ranges.get(category, (50000, 5000000))
    # Round to nearest 10,000 INR
    return int(round(random.randint(low, high), -4))

def generate_dataset():
    random.seed(SEED)
    
    records = []
    record_counter = 1
    
    # 5 categories * 8 = 40 records total
    category_pool = CATEGORIES * 8
    random.shuffle(category_pool)
    
    for category in category_pool:
        record_id = f"CRED-LN-{record_counter:03d}"
        status = random.choice(STATUSES)
        loan_amount_inr = get_realistic_loan_amount(category)
        days_since_created = random.randint(0, 30)
        
        # Seeded weighted probability for fraud review (target between 10% and 30%)
        flagged_for_fraud_review = random.choices([True, False], weights=[0.20, 0.80])[0]
        
        record = {
            "record_id": record_id,
            "category": category,
            "status": status,
            "loan_amount_inr": loan_amount_inr,
            "days_since_created": days_since_created,
            "flagged_for_fraud_review": flagged_for_fraud_review
        }
        records.append(record)
        record_counter += 1

    return records

def validate_and_save():
    # 1. Delete previous loans JSON file if it exists
    if DATA_FILE.exists():
        DATA_FILE.unlink()
        print(f"Deleted existing dataset file: {DATA_FILE}")

    # Ensure data directory exists under project root
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    # Generate new dataset
    applications = generate_dataset()

    # Save to JSON at root/data/loans.json
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(applications, f, indent=4)
    print(f"Successfully generated and saved new dataset to {DATA_FILE}")

    # 2. Print Validation Metrics
    print("\n--- DATASET VALIDATION REPORT ---")
    print(f"Total Records: {len(applications)}")

    print("\nCategory Counts:")
    for cat in CATEGORIES:
        count = sum(1 for r in applications if r["category"] == cat)
        print(f"  • {cat}: {count} (≥3 required: {'PASS' if count >= 3 else 'FAIL'})")

    print("\nStatus Counts:")
    for stat in STATUSES:
        count = sum(1 for r in applications if r["status"] == stat)
        print(f"  • {stat}: {count} (≥1 required: {'PASS' if count >= 1 else 'FAIL'})")

    fraud_count = sum(1 for r in applications if r["flagged_for_fraud_review"])
    fraud_pct = (fraud_count / len(applications)) * 100
    print(f"\nFraud Review Flagged Percentage: {fraud_pct:.1f}% ({fraud_count}/{len(applications)})")
    print(f"Target Band (10% - 30%): {'PASS' if 10 <= fraud_pct <= 30 else 'FAIL'}\n")

if __name__ == "__main__":
    validate_and_save()