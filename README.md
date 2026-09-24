# Public AI Challenge - Team 34

## Test the OpenAI API

Install the project dependencies:

```sh
uv sync
```

If `.env` does not exist yet, copy `.env.example` to `.env`. Set `OPENAI_API_KEY` in `.env`, then run the CLI from the repository root:

```sh
uv run python scripts/test_openai.py
```

To send a different prompt:

```sh
uv run python scripts/test_openai.py "Say hello in German."
```

The default prompt asks for the capital of Switzerland. The script sends one request to `gpt-6-luna` with low reasoning effort and prints the response.

## Problem

- 2110 municipalities in Switzerland
- Almost every municipalitys website and online services have different shapes

## Solution

- ...


# Work Packages
- Data Akquisition
  -Scrape the Services of the communities
  -Create a Data Model
  -Check eCH070
  -MCP Server
- User Experience
  -Narrative, Screens Conversation Flow
- System Architecture
  -Tech stack, Reference Architecture, Components -> Implementation
- Quality Assurance
  -LLM-as-a-Judge, Scalalbility, Liefcycle Management
- Deployment and Go-To Market Strategy
  - Adoption
