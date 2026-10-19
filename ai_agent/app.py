"""
Simple CLI to test the agent.
Usage:
    python -m ai_agent.app
"""

from ai_agent.agent import chat_with_history


def main():
    print("Volve Field AI Agent  (type 'quit' to exit)\n")
    history = []

    while True:
        try:
            user = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye.")
            break

        if not user:
            continue
        if user.lower() in {"quit", "exit", "q"}:
            print("Bye.")
            break

        try:
            answer, history = chat_with_history(user, history=history)
            print(f"\nAgent: {answer}\n")
        except Exception as e:
            print(f"\nError: {e}\n")


if __name__ == "__main__":
    main()
