"""The agent: system prompt + Gemini + a tool-calling loop that records a trace."""

import json
import os

from dotenv import load_dotenv
from google import genai
from google.genai import types

from tools import TOOLS

load_dotenv()

# Change the model here, or set GEMINI_MODEL in your .env file.
MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")

SYSTEM_PROMPT = """
# Role
You are Little Monkey, the friendly customer service assistant of Water Monkey
Guesthouse (水猴子民宿), a small family-run guesthouse with sixteen rooms.
You help guests with questions about the guesthouse, its rooms and the price of a stay.

# Grounding: answer only from tool results
- Use a tool before you answer any question about the guesthouse. Answer only with
  facts that a tool returned. Never use your own knowledge about rooms, prices,
  rules, opening hours or the area.
- If a tool says the information was not found, tell the guest you do not have that
  information. Do not guess. Offer to connect them with the owner (transfer_to_human).
- Never do price maths yourself. Always use calculate_stay for any price.

# Scope: stay with the guesthouse
- Only help with Water Monkey Guesthouse. If the guest asks about anything else
  (other hotels, sightseeing plans, weather, homework, coding, news), politely say
  you can only help with questions about the guesthouse, and suggest what you can help with.
- You cannot make, change or cancel a booking yourself. For these, use transfer_to_human.

# Routing: which tool for which question
- check-in or check-out time, address, parking, breakfast, payment, deposit,
  cancellation, discount, extra bed rules, pets rules, Wi-Fi, smoking, contact -> get_info
- which rooms there are, which rooms are free, rooms for a number of guests,
  river view, pet-friendly rooms, the price per night of a room -> search_rooms
- the total price of a stay, how much for N nights, deposit amount -> calculate_stay.
  If it returns room choices, show them and ask the guest to choose one room.
- complaints, special requests, booking, changing or cancelling a booking, or
  anything the other tools cannot answer -> transfer_to_human

# Language and format
- Reply in the guest's language: in English if they write in English, and in
  Traditional Chinese (繁體中文) if they write in Chinese. In Chinese, use the
  room_type_zh names (for example 家庭房).
- Keep replies short and friendly: two to four sentences, or a short list for rooms.
- Write prices as NT$ with commas, for example NT$7,560.
""".strip()


def make_client():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is missing. Put it in your .env file.")
    return genai.Client(api_key=api_key)


def make_config(extra_instruction=""):
    system = SYSTEM_PROMPT + ("\n\n" + extra_instruction if extra_instruction else "")
    return types.GenerateContentConfig(
        system_instruction=system,
        tools=TOOLS,
        # We run the tools ourselves so that we can record the tool trace.
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        temperature=0.2,
    )


CONFIG = make_config()

TOOL_MAP = {f.__name__: f for f in TOOLS}


# ---------- reply language: decided by the program, not by the model ----------

LANGUAGES = {
    "zh": ("繁體中文", "Reply in Traditional Chinese (繁體中文). Use the room_type_zh names, for example 家庭房."),
    "en": ("English", "Reply in English. Use the English room_type names."),
}


def detect_language(text):
    """Return "zh" if the message has Chinese characters, otherwise "en"."""
    chinese = sum(1 for ch in text if "一" <= ch <= "鿿")
    return "zh" if chinese > 0 else "en"


def history_to_contents(history):
    """Turn Gradio chat history [{'role','content'}, ...] into Gemini contents."""
    contents = []
    for msg in history:
        role = "user" if msg["role"] == "user" else "model"
        text = msg["content"] if isinstance(msg["content"], str) else str(msg["content"])
        contents.append(types.Content(role=role, parts=[types.Part(text=text)]))
    return contents


def run_agent(client, history, user_message, max_steps=5):
    """Send the message, run any tools Gemini asks for, and return
    (reply, trace, language_name).

    trace is a list of dicts: {"tool": name, "args": {...}, "result": {...}}
    """
    lang = detect_language(user_message)
    language_name, language_rule = LANGUAGES[lang]
    config = make_config(f"# Reply language for this message (set by the program)\n{language_rule}")
    print(f"[language] {language_name}")

    contents = history_to_contents(history)
    contents.append(types.Content(role="user", parts=[types.Part(text=user_message)]))
    trace = []

    for _ in range(max_steps):
        response = client.models.generate_content(model=MODEL, contents=contents, config=config)
        calls = response.function_calls or []
        if not calls:
            return (response.text or "").strip(), trace, language_name

        contents.append(response.candidates[0].content)
        result_parts = []
        for call in calls:
            args = dict(call.args or {})
            func = TOOL_MAP.get(call.name)
            try:
                result = func(**args) if func else {"error": f"Unknown tool {call.name}"}
            except Exception as e:  # show tool errors to the model instead of crashing
                result = {"error": str(e)}
            trace.append({"tool": call.name, "args": args, "result": result})
            print(f"[tool] {call.name}({json.dumps(args, ensure_ascii=False)})")
            result_parts.append(types.Part.from_function_response(name=call.name, response={"result": result}))
        contents.append(types.Content(role="user", parts=result_parts))

    sorry = {"zh": "抱歉，我無法完成這個問題，請聯絡老闆：0912-345-678。",
             "en": "Sorry, I could not finish that. Please contact the owner at 0912-345-678."}
    return sorry[lang], trace, language_name


def first_tool_choice(client, question):
    """Ask one question and return the name of the first tool Gemini picks (or None).
    Used by test_tool_choice.py. The tool is not run."""
    contents = [types.Content(role="user", parts=[types.Part(text=question)])]
    response = client.models.generate_content(model=MODEL, contents=contents, config=CONFIG)
    calls = response.function_calls or []
    return calls[0].name if calls else None
