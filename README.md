# Water Monkey Guesthouse 水猴子民宿 – AI Customer Service Agent

A customer service agent for a small family-run guesthouse. It answers guests' questions
using a SQLite database built from two CSV files and four tools, with Gemini as the model
and a Gradio chat screen that shows the tool trace.

## Files

| File | What it is |
| --- | --- |
| `guesthouse_info.csv` | Information table: 11 topics (check-in, parking, breakfast, ...) |
| `rooms.csv` | Records table: 16 rooms with type, guests, price, view, pets, availability |
| `tools.py` | Builds `guesthouse.db` from the CSV files, and the four tools |
| `agent.py` | System prompt, Gemini setup and the tool-calling loop |
| `app.py` | Gradio chat screen with the tool trace |
| `test_tool_choice.py` | Tool-choice test (13 questions) |
| `requirements.txt` | Python packages |
| `.env.example` | Example of the `.env` file (the real `.env` is not uploaded) |

## Tools

| Tool | Kind | Example question |
| --- | --- | --- |
| `get_info` | Look up information | "Is there parking?" |
| `search_rooms` | Look up records | "Do you have a free room for four people?" |
| `calculate_stay` | Calculate (in code) | "How much is three nights in room 203?" |
| `transfer_to_human` | Hand over to a person | "I want to complain." |

## How to run

```bash
pip install -r requirements.txt
cp .env.example .env        # then put your Gemini API key in .env
python app.py               # opens the chat screen
python test_tool_choice.py  # runs the tool-choice test
```

Get a free Gemini API key at https://aistudio.google.com/apikey.
