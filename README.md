# Agent-as-Coder Challenge

This project features an AI agent that automatically writes custom Python parsers for bank statement PDFs.

## How the Agent Works

The agent operates on a "plan, code, test, self-fix" loop built with LangGraph. It first analyzes the task and creates a detailed plan. It then uses an LLM to generate the Python parser code based on that plan. The agent saves this code and executes a test to compare the parser's output against a known-correct CSV file. If the test fails, the agent reads the error, refines its plan, and retries up to two more times.

## How to Run

1.  Clone the repository.
2.  Install the required dependencies:
    `pip install langgraph langchain-groq pandas pdfplumber`
3.  Create a GroqCloud account to get a free API key.
4.  Paste your API key into the `llm` definition in `agent.py`.
5.  Run the agent from the command line:
    `python agent.py --target icici`
