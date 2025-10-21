# core/utils.py
import numpy_financial as npf
import re
from typing import Optional, Dict, List, Any
import sqlite3 # Import for DB access if needed here
from .constants import LOAN_DB_PATH # Import DB path

def calculate_prepayment_impact(
    principal: float,
    annual_rate: float,
    tenure_months: int,
    prepayment_amount: float
) -> dict:
    """
    Simulates the impact of a one-time prepayment on a loan.
    Focuses on tenure reduction.
    """
    try:
        if principal <= 0 or annual_rate < 0 or tenure_months <= 0 or prepayment_amount < 0:
             # Allow 0% interest rate
            raise ValueError("Loan principal and tenure must be positive. Prepayment cannot be negative.")
        if annual_rate == 0:
             monthly_rate = 0
             original_emi = principal / tenure_months if tenure_months > 0 else 0
        else:
             monthly_rate = (annual_rate / 100) / 12 # Ensure rate is decimal
             original_emi = npf.pmt(monthly_rate, tenure_months, -principal)

        if original_emi <= 0: # Avoid issues with nper if EMI is zero/negative
            return {
                "original_emi": 0,
                "new_emi_unchanged": 0,
                "new_tenure_months": 0,
                "interest_saved": 0,
                 "message": "Original EMI calculation resulted in zero or negative value."
            }


        # Assume prepayment happens and reduces the principal balance
        new_principal = principal - prepayment_amount

        if new_principal <= 0:
            # Loan is fully paid off
            return {
                "original_emi": round(original_emi, 2),
                "new_emi_unchanged": 0,
                "new_tenure_months": 0,
                "interest_saved": "Loan Foreclosed",
                "message": f"Prepayment of ₹{prepayment_amount:,.2f} fully pays off the loan."
            }

        # Calculate new tenure keeping EMI the same
        if monthly_rate == 0:
             # Handle 0% interest rate case for nper equivalent
             new_tenure = new_principal / original_emi if original_emi > 0 else 0
        else:
             # Use numpy_financial.nper
             # Ensure correct signs: rate, payment (negative), present_value (positive)
             new_tenure = npf.nper(monthly_rate, -original_emi, new_principal)


        new_tenure_months = int(round(new_tenure)) if new_tenure > 0 else 0

        # Calculate interest saved (approximate)
        original_total_paid = original_emi * tenure_months
        new_total_paid_projection = (original_emi * new_tenure_months) + prepayment_amount
        # Note: Actual interest saved depends on when prepayment occurs. This is simplified.
        original_total_interest = original_total_paid - principal
        new_total_interest = (original_emi * new_tenure_months) - new_principal
        interest_saved = original_total_interest - new_total_interest


        return {
            "original_emi": round(original_emi, 2),
            "new_emi_unchanged": round(original_emi, 2),
            "original_tenure_months": tenure_months,
            "new_tenure_months": new_tenure_months,
            "interest_saved": round(interest_saved, 2),
            "months_reduced": tenure_months - new_tenure_months,
            "message": f"Prepaying ₹{prepayment_amount:,.2f} could reduce tenure by {tenure_months - new_tenure_months} months."
        }

    except Exception as e:
        print(f"Error in prepayment calculation: {e}")
        return {"error": f"Calculation failed: {str(e)}"}


def extract_loan_params_from_query(query: str) -> Dict[str, Optional[float]]:
    """Simple regex-based extraction of loan parameters for calculator."""
    params = {"loan_amount": None, "interest_rate": None, "tenure_months": None, "prepayment_amount": None}
    query_lower = query.lower()

    # Loan Amount (handles lakh/crore roughly)
    amount_match = re.search(r"(\d+(?:,\d+)*(?:\.\d+)?)\s*(?:lakh|lac)", query_lower)
    if amount_match:
        try: params["loan_amount"] = float(amount_match.group(1).replace(",", "")) * 100000
        except: pass
    else:
        amount_match = re.search(r"(\d+(?:,\d+)*(?:\.\d+)?)\s*crore", query_lower)
        if amount_match:
            try: params["loan_amount"] = float(amount_match.group(1).replace(",", "")) * 10000000
            except: pass
        else:
             # Look for plain numbers with currency symbols or context
             amount_match = re.search(r"(?:rs\.?|₹|inr)\s*(\d+(?:,\d+)*(?:\.\d+)?)", query_lower) or \
                            re.search(r"(\d+(?:,\d+)*(?:\.\d+)?)\s*(?:rs\.?|rupees|loan)", query_lower) # order matters
             if amount_match:
                  try: params["loan_amount"] = float(amount_match.group(1).replace(",", ""))
                  except: pass


    # Interest Rate
    rate_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:%|percent)", query_lower)
    if rate_match:
        try: params["interest_rate"] = float(rate_match.group(1))
        except: pass

    # Tenure (Years or Months)
    tenure_match = re.search(r"(\d+)\s*(?:year|yr)s?", query_lower)
    if tenure_match:
        try: params["tenure_months"] = int(tenure_match.group(1)) * 12
        except: pass
    else:
        tenure_match = re.search(r"(\d+)\s*(?:month|mo)s?", query_lower)
        if tenure_match:
             try: params["tenure_months"] = int(tenure_match.group(1))
             except: pass


    # Prepayment Amount
    prepay_match = re.search(r"prepay(?:ment)?\s*(?:of)?\s*(?:rs\.?|₹|inr)?\s*(\d+(?:,\d+)*(?:\.\d+)?)", query_lower)
    if prepay_match:
        try: params["prepayment_amount"] = float(prepay_match.group(1).replace(",", ""))
        except: pass

    print(f"Extracted Params: {params}")
    return params

# --- Customer Data Fetching Logic (Moved from WorkflowEngine) ---

def _extract_customer_ids_from_text(text: str) -> List[int]:
    """Extracts potential customer IDs (numeric) from text."""
    ids_int = []
    if not text:
        return ids_int
    # Simple pattern: look for numbers following 'customer', 'cust', 'id'
    pattern = r"(?:customer|cust|id)[_\s]*(?:id|is|:)?\s*(\d+)"
    matches = re.findall(pattern, text, re.IGNORECASE)
    unique_ids_str = set(matches)
    for match in unique_ids_str:
        try:
            ids_int.append(int(match))
        except ValueError:
             print(f"Warning: Found non-integer potential customer ID '{match}'")
    return ids_int

def fetch_customer_data(customer_ids: List[int]) -> List[Dict[str, Any]]:
    """Fetches loan data from SQLite for a list of customer IDs."""
    if not customer_ids:
        return []

    # Ensure unique IDs
    unique_ids = sorted(list(set(customer_ids)))

    try:
        print(f"DB Fetch: Getting data for customer IDs: {unique_ids}")
        with sqlite3.connect(LOAN_DB_PATH) as conn:
            conn.row_factory = sqlite3.Row # Return dict-like rows
            cursor = conn.cursor()
            placeholders = ",".join("?" * len(unique_ids))
            sql = f"""
                SELECT customer_id, loan_amount, interest_rate, tenure_months,
                       monthly_emi, status, loan_id, next_due_date, amount_paid
                FROM loan_data
                WHERE customer_id IN ({placeholders})
            """
            cursor.execute(sql, unique_ids)
            rows = cursor.fetchall()
            results = [dict(row) for row in rows]
            if not results:
                 print(f"DB Fetch: No data found for customer IDs: {unique_ids}")
            return results
    except sqlite3.Error as e:
        print(f"❌ Database error fetching customer data: {e}")
        return []
    except Exception as e:
        print(f"❌ Unexpected error fetching customer data: {e}")
        return []