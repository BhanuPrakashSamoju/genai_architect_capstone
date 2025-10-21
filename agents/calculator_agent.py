# agents/calculator_agent.py
from typing import Dict, Any, Optional

# Core components
from core.llm_provider import get_llm
from core.state import AgentGraphState
from core.utils import calculate_prepayment_impact, extract_loan_params_from_query # Use utils
from langchain_core.messages import AIMessage

# --- LangGraph Node Function ---
def calculator_node(state: AgentGraphState) -> Dict[str, Any]:
    """Extracts parameters, performs calculation, and formats response."""
    print("--- What-If Calculator Node ---")
    query = state["query"]
    customer_data = state.get("customer_data") # Optional customer data
    messages = list(state.get("messages", []))
    outcome = "error"
    final_answer = "Sorry, I couldn't perform the calculation."
    error_message = None

    try:
        llm = get_llm(temperature=0.0) # Use 0 temp for extraction/consistency

        # 1. Parameter Extraction (Combine simple extraction and LLM refinement)
        extracted_params = extract_loan_params_from_query(query)

        # Use LLM to fill gaps or confirm parameters if needed, especially tenure/amount
        # Simplified: Use extracted params directly if essential ones are present.
        # If not, use LLM to extract from the query.

        loan_amount = extracted_params.get("loan_amount")
        interest_rate = extracted_params.get("interest_rate")
        tenure_months = extracted_params.get("tenure_months")
        prepayment_amount = extracted_params.get("prepayment_amount")

        # Use customer data if parameters are missing from query
        if customer_data:
             # Assuming single customer for simplicity, could enhance for multiple
             cust_loan = customer_data[0]
             if loan_amount is None: loan_amount = cust_loan.get("loan_amount")
             if interest_rate is None: interest_rate = cust_loan.get("interest_rate")
             if tenure_months is None: tenure_months = cust_loan.get("tenure_months")
             # Calculate outstanding if needed for prepayment context
             outstanding = cust_loan.get("loan_amount", 0) - cust_loan.get("amount_paid", 0)
             if prepayment_amount is not None and prepayment_amount > outstanding:
                  # [cite_start]Handle validation based on Phase 3 Fallback [cite: 515-516]
                  outcome = "error" # Or potentially "clarification_needed"
                  error_message = f"Prepayment amount (₹{prepayment_amount:,.2f}) exceeds outstanding balance (₹{outstanding:,.2f})."
                  final_answer = f"{error_message} Would you like to simulate a full loan closure instead?"
                  # No calculation performed in this case
                  return {
                     "messages": messages + [AIMessage(content=final_answer)], # Add clarification
                     "agent_outcome": outcome,
                     "final_answer": None, # No final calc answer
                     "error_message": error_message
                 }


        # Check if essential parameters are available
        if loan_amount is None or interest_rate is None or tenure_months is None:
            # If crucial info missing, use LLM to ask for clarification
            print("Calculator: Essential parameters missing. Asking LLM for clarification prompt.")
            clarification_prompt = f"""The user asked: "{query}"
I need the Loan Amount, Annual Interest Rate (%), and Loan Tenure (in months or years) to perform the calculation.
Please ask the user politely to provide the missing information."""
            clarification_message = llm.invoke(clarification_prompt).content.strip()
            final_answer = clarification_message
            outcome = "clarification_needed" # Or handle as error
            error_message = "Missing essential parameters for calculation."

        else:
            # 2. Perform Calculation using utility function
            print(f"Calculating for: Amount={loan_amount}, Rate={interest_rate}, Tenure={tenure_months}, Prepay={prepayment_amount}")
            # Decide which calculation based on query intent (prepayment vs basic EMI)
            # Simplified: Always run prepayment if amount exists, else basic EMI calc
            if prepayment_amount is not None and prepayment_amount > 0:
                 calc_result = calculate_prepayment_impact(
                     principal=loan_amount,
                     annual_rate=interest_rate,
                     tenure_months=int(tenure_months),
                     prepayment_amount=prepayment_amount
                 )
            else:
                 # Perform basic EMI calculation (or generate schedule) if needed
                 # calc_result = calculate_basic_emi(...)
                 # For now, focus on prepayment impact as primary 'what-if'
                 calc_result = {"message": "Please specify a prepayment amount to simulate its impact.", "error": "No prepayment specified"} # Placeholder

            # 3. Format Response
            if "error" in calc_result:
                final_answer = f"Calculation Error: {calc_result['error']}"
                error_message = calc_result['error']
                outcome = "error"
            else:
                 # Create a user-friendly summary string
                 summary = f"Calculation Results for Loan (₹{loan_amount:,.0f} @ {interest_rate}% for {tenure_months} months):\n"
                 if prepayment_amount:
                     summary += f"- Original EMI: ₹{calc_result.get('original_emi', 'N/A'):,.2f}\n"
                     summary += f"- With Prepayment of ₹{prepayment_amount:,.2f}:\n"
                     summary += f"  - Tenure reduces by: {calc_result.get('months_reduced', 'N/A')} months (New Tenure: {calc_result.get('new_tenure_months', 'N/A')} months)\n"
                     summary += f"  - Estimated Interest Saved: ₹{calc_result.get('interest_saved', 'N/A'):,.2f}\n"
                     summary += f"  - EMI remains: ₹{calc_result.get('new_emi_unchanged', 'N/A'):,.2f}"
                 else:
                     # Add formatting for basic EMI calculation if implemented
                     summary += calc_result.get('message', 'No prepayment specified for simulation.')

                 final_answer = summary
                 outcome = "success"

    except Exception as e:
        print(f"❌ Calculator Node Error: {e}")
        error_message = f"Calculator failed: {str(e)}"
        outcome = "error"
        final_answer = "Sorry, I encountered an error during the calculation."

    # Update state
    messages.append(AIMessage(content=final_answer)) # Always add the final message
    return {
        "messages": messages,
        "agent_outcome": outcome,
        "final_answer": final_answer if outcome == "success" else None,
        "error_message": error_message,
        # Indicate clarification needed if parameters were missing
        "clarification_needed": (outcome == "clarification_needed"),
        "clarification_message": final_answer if (outcome == "clarification_needed") else None
    }