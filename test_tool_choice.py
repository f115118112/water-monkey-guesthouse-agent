"""Tool-choice test: does Gemini pick the right tool for each question?

Run:  python test_tool_choice.py
Take a screenshot of the output for part 5.2 of the report.
"""

import time

from agent import MODEL, first_tool_choice, make_client

TESTS = [
    ("What time is check-in?", "get_info"),
    ("Is there parking for my car?", "get_info"),
    ("Do you serve breakfast?", "get_info"),
    ("可以帶狗嗎？有什麼規定？", "get_info"),
    ("What is your cancellation policy?", "get_info"),
    ("Do you have a free room for four people?", "search_rooms"),
    ("Which rooms have a river view?", "search_rooms"),
    ("有哪些房間可以帶寵物？", "search_rooms"),
    ("How much is three nights in room 203?", "calculate_stay"),
    ("家庭套房住兩晚加一張床多少錢？", "calculate_stay"),
    ("What is the total for 2 nights in room 103 with my cat?", "calculate_stay"),
    ("I want to complain, the room was dirty.", "transfer_to_human"),
    ("Can you book room 204 for me next Friday?", "transfer_to_human"),
]

client = make_client()
print(f"Tool-choice test with {MODEL}\n")
correct = 0
for i, (question, expected) in enumerate(TESTS, 1):
    got = first_tool_choice(client, question)
    ok = got == expected
    correct += ok
    print(f"{i:2}. {'OK  ' if ok else 'MISS'} expected {expected:18} got {str(got):18} | {question}")
    time.sleep(1)  # stay under the free-tier rate limit

print(f"\nScore: {correct}/{len(TESTS)} = {correct / len(TESTS):.0%}")
