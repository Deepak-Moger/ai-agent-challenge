#
# 1. Start with all the imports at the top
#
import os
import sys
import argparse
import subprocess
import pandas as pd
from typing import TypedDict, List
from langchain_groq import ChatGroq
from langgraph.graph import StateGraph, END

#
# 2. Define the Agent's "Memory" (the AgentState class)
#
class AgentState(TypedDict):
    target_bank: str
    pdf_path: str
    csv_path: str
    plan: str
    generated_code: str
    test_result: str
    attempts_left: int

#
# 3. Initialize the LLM
#
llm = ChatGroq(
    model="gemma2-9b-it",
    groq_api_key="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" # <-- PASTE YOUR NEW KEY HERE
)

#
# 4. Add the "Thinking" Nodes (the functions)
#
def planner_node(state: AgentState):
    print("---PLANNING---")
    prompt = f"""
You are an expert Python programmer. Your goal is to create a plan to write a Python script that parses a bank statement PDF.
The target bank is '{state['target_bank']}'.
The script must have a function `parse(pdf_path)` that returns a pandas DataFrame.
The output DataFrame must match the structure of this CSV: '{state['csv_path']}'.

Here is the winning strategy:
1. Use the 'pdfplumber' library to open the PDF.
2. On the first page, use the 'extract_tables()' method to find the main transaction table.
3. Convert the first table found into a pandas DataFrame.
4. The table has headers in its first row. Use these for the DataFrame columns.
5. Clean the DataFrame by doing the following:
    - Drop the 'Balance' column, as it is not needed.
    - Rename the column 'Debit Amt' to 'Debit'.
    - Rename the column 'Credit Amt' to 'Credit'.
    - Fill any empty or missing values in the 'Debit' and 'Credit' columns with 0.
    - Make sure the 'Debit' and 'Credit' columns are a numeric type (like float).
6. Ensure the final DataFrame's columns and data match the CSV at '{state['csv_path']}'.

Here was the result from the last attempt: {state['test_result']}.
Based on this, create a short, step-by-step plan to write a better parser.
"""
    response = llm.invoke(prompt)
    state['plan'] = response.content
    return state

def code_generator_node(state: AgentState):
    print("---GENERATING CODE---")
    prompt = f"""
    Based on the following plan, write the full Python code for the parser.
    Plan: {state['plan']}

    The code must be a single Python script. It must define a function `parse(pdf_path)` that takes a file path and returns a pandas DataFrame.
    Use libraries like pandas and pypdf. Do not include any example usage, just the function and necessary imports.
    """
    response = llm.invoke(prompt)
    state['generated_code'] = response.content.strip().replace('```python', '').replace('```', '')
    return state

def test_node(state: AgentState):
    print("---TESTING CODE---")
    parser_path = os.path.join("custom_parsers", f"{state['target_bank']}_parser.py")
    os.makedirs("custom_parsers", exist_ok=True)

    with open(parser_path, "w") as f:
        f.write(state['generated_code'])

    test_runner_code = f"""
import pandas as pd
from {parser_path.replace(os.sep, '.').replace('.py', '')} import parse

try:
    expected_df = pd.read_csv('{state['csv_path']}')
    actual_df = parse('{state['pdf_path']}')

    if expected_df.equals(actual_df):
        print("success")
    else:
        print("Error: DataFrame does not match the expected output.")
        print("Expected:\\n", expected_df)
        print("Actual:\\n", actual_df)
except Exception as e:
    print(f"Execution Error: {{e}}")
"""
    
    with open("test_runner.py", "w") as f:
        f.write(test_runner_code)

    result = subprocess.run(
        [sys.executable, "test_runner.py"],
        capture_output=True,
        text=True
    )

    if "success" in result.stdout:
        print("---TEST PASSED---")
        state['test_result'] = "success"
    else:
        print("---TEST FAILED---")
        error_message = result.stdout + result.stderr
        state['test_result'] = error_message
    
    state['attempts_left'] -= 1
    return state

#
# 5. Build the Graph
#
workflow = StateGraph(AgentState)
workflow.add_node("planner", planner_node)
workflow.add_node("code_generator", code_generator_node)
workflow.add_node("tester", test_node)
workflow.set_entry_point("planner")
workflow.add_edge("planner", "code_generator")
workflow.add_edge("code_generator", "tester")

def should_continue(state: AgentState):
    if state['test_result'] == "success" or state['attempts_left'] == 0:
        return "end"
    else:
        return "continue"

workflow.add_conditional_edges(
    "tester",
    should_continue,
    {"continue": "planner", "end": END}
)
app = workflow.compile()

#
# 6. Add the final part to Run the Agent from the command line
#
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", required=True, help="The target bank, e.g., 'icici'")
    args = parser.parse_args()

    initial_state = {
        "target_bank": args.target,
        "pdf_path": os.path.join("data", args.target, f"{args.target}_sample.pdf"),
        "csv_path": os.path.join("data", args.target, f"{args.target}_sample.csv"),
        "plan": "",
        "generated_code": "",
        "test_result": "No test run yet.",
        "attempts_left": 3,
    }

    for event in app.stream(initial_state):
        print(event)