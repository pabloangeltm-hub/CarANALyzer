"""
Send a prompt to Claude and return the response. Supports system prompts and file context.

Usage:
    python tools/ask_claude.py --prompt "Summarize this" --file .tmp/data.txt
    python tools/ask_claude.py --prompt "What is 2+2?"

    Or as a module:
    from tools.ask_claude import ask
    response = ask("Your prompt here", context="optional extra context")
"""
import argparse
import os
from dotenv import load_dotenv
import anthropic

load_dotenv()


def ask(
    prompt: str,
    context: str = "",
    system: str = "",
    model: str = "claude-sonnet-4-6",
    max_tokens: int = 4096,
) -> str:
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    user_content = f"{context}\n\n{prompt}".strip() if context else prompt

    kwargs = {
        "model": model,
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": user_content}],
    }
    if system:
        kwargs["system"] = system

    message = client.messages.create(**kwargs)
    return message.content[0].text


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ask Claude a question")
    parser.add_argument("--prompt", required=True, help="Prompt to send")
    parser.add_argument("--file", help="File whose contents are added as context")
    parser.add_argument("--system", default="", help="System prompt")
    parser.add_argument("--model", default="claude-sonnet-4-6")
    parser.add_argument("--output", help="Save response to this file")
    args = parser.parse_args()

    context = ""
    if args.file:
        with open(args.file, "r", encoding="utf-8") as f:
            context = f.read()

    response = ask(args.prompt, context=context, system=args.system, model=args.model)

    if args.output:
        os.makedirs(os.path.dirname(args.output) if os.path.dirname(args.output) else ".", exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(response)
        print(f"[OK] Response saved to {args.output}")
    else:
        print(response)
