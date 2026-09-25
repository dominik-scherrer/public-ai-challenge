"""Make a small GPT-6 Luna API request using the repository's .env file."""

import argparse
import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI


def main() -> None:
    parser = argparse.ArgumentParser(description="Test the OpenAI API with GPT-6 Luna.")
    parser.add_argument(
        "prompt",
        nargs="?",
        default="What is the capital of Switzerland?",
        help="Prompt to send (default: What is the capital of Switzerland?)",
    )
    args = parser.parse_args()

    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        parser.error("OPENAI_API_KEY is missing. Add it to the repository's .env file.")

    response = OpenAI(api_key=api_key).responses.create(
        model="gpt-6-luna",
        reasoning={"effort": "low"},
        input=args.prompt,
    )
    print(response.output_text)


if __name__ == "__main__":
    main()
