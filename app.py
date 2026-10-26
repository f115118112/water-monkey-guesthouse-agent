"""Gradio chat screen for Water Monkey Guesthouse (clean, Google-style look).

Run:  python app.py   then open the link it prints (usually http://127.0.0.1:7860).
"""

from html import escape

import gradio as gr

from agent import MODEL, make_client, run_agent

client = make_client()

EMPTY_TRACE = '<div class="trace-empty">Tool steps will show here after you send a message.</div>'

TOOL_LABELS = {
    "get_info": ("📖", "Looked up guesthouse information"),
    "search_rooms": ("🔎", "Searched the room list"),
    "calculate_stay": ("🧮", "Calculated the price"),
    "transfer_to_human": ("📞", "Handed over to the owner"),
}


def _money(n):
    return f"NT${n:,}"


def _describe_args(args):
    if not args:
        return "no details"
    return ", ".join(f"{k.replace('_', ' ')}: {v}" for k, v in args.items() if v not in ("", 0, False, None)) or "all"


def _result_html(tool, r):
    """Turn a tool result into plain, readable HTML (no JSON)."""
    if r.get("error"):
        return f'<p class="bad">Error: {escape(str(r["error"]))}</p>'

    if tool == "get_info":
        if r.get("found"):
            return f'<p><b>{escape(r["topic"])}</b>: {escape(r["content"])}</p>'
        return (f'<p class="bad">Not found. {escape(r["message"])}</p>'
                f'<p class="muted">Topics we have: {escape(", ".join(r["available_topics"]))}</p>')

    if tool == "search_rooms":
        if not r.get("found"):
            return f'<p class="bad">{escape(r["message"])}</p>'
        rows = "".join(
            f'<tr><td>{escape(x["room_no"])}</td><td>{escape(x["room_type"])}<br>'
            f'<span class="muted">{escape(x["room_type_zh"])}</span></td>'
            f'<td>{x["max_guests"]}</td><td>{_money(x["price_per_night"])}</td>'
            f'<td>{"✅" if x["available"] == "yes" else "❌"}</td></tr>'
            for x in r["rooms"]
        )
        return (f'<p>Found {r["count"]} room(s).</p><table><tr><th>Room</th><th>Type</th>'
                f'<th>Guests</th><th>Per night</th><th>Free</th></tr>{rows}</table>')

    if tool == "calculate_stay":
        if not r.get("ok"):
            html = f'<p class="bad">{escape(r["message"])}</p>'
            if r.get("choices"):
                items = "".join(f'<li>Room {escape(c["room_no"])} ({escape(c["view"])} view): '
                                f'{_money(c["price_per_night"])} per night</li>' for c in r["choices"])
                html += f'<ul>{items}</ul>'
            if r.get("room_types"):
                html += f'<p class="muted">Room types: {escape(", ".join(r["room_types"]))}</p>'
            return html
        lines = [f'{_money(r["price_per_night"])} × {r["nights"]} night(s) = {_money(r["room_total"])}']
        if r["discount"]:
            lines.append(f'10% off for 3+ nights: −{_money(r["discount"])}')
        if r["extra_bed_total"]:
            lines.append(f'Extra bed: +{_money(r["extra_bed_total"])}')
        if r["pet_fee"]:
            lines.append(f'Pet fee: +{_money(r["pet_fee"])}')
        body = "".join(f"<li>{escape(l)}</li>" for l in lines)
        return (f'<p>{escape(r["room"])}</p><ul>{body}</ul>'
                f'<p class="total">Total {_money(r["total"])}</p>'
                f'<p class="muted">Deposit (30%): {_money(r["deposit_30_percent"])}</p>')

    if tool == "transfer_to_human":
        return f'<p>{escape(r["contact"])}</p>'

    return f'<p>{escape(str(r))}</p>'


def format_trace(trace, language=None):
    badge = (f'<div class="lang">🌐 Reply language (chosen by the program): <b>{escape(language)}</b></div>'
             if language else "")
    if not trace:
        return badge + '<div class="trace-empty">No tool was used for this message.</div>'
    cards = [badge]
    for i, step in enumerate(trace, 1):
        icon, label = TOOL_LABELS.get(step["tool"], ("🔧", step["tool"]))
        cards.append(
            f'<div class="card"><div class="card-head"><span class="icon">{icon}</span>'
            f'<div><div class="step">Step {i} · {escape(step["tool"])}</div>'
            f'<div class="label">{label}</div></div></div>'
            f'<div class="asked">Asked for: {escape(_describe_args(step["args"]))}</div>'
            f'<div class="result">{_result_html(step["tool"], step["result"])}</div></div>'
        )
    return "".join(cards)


def respond(user_message, history):
    if not user_message.strip():
        return "", history, gr.update()
    reply, trace, language = run_agent(client, history, user_message)
    history = history + [
        {"role": "user", "content": user_message},
        {"role": "assistant", "content": reply},
    ]
    return "", history, format_trace(trace, language)


CSS = """
:root { --g-blue:#1a73e8; --g-border:#dadce0; --g-text:#202124; --g-muted:#5f6368; --g-bg:#f8f9fa; }
.gradio-container { max-width: 1200px !important; margin: 0 auto !important; background: #fff !important; }
footer { display: none !important; }
#header { text-align: center; padding: 28px 0 8px; }
#header h1 { font-size: 40px; font-weight: 500; margin: 0; letter-spacing: -0.5px; color: var(--g-text); }
#header h1 .c1{color:#4285f4} #header h1 .c2{color:#ea4335} #header h1 .c3{color:#fbbc05} #header h1 .c4{color:#34a853}
#header p { color: var(--g-muted); margin: 6px 0 0; font-size: 15px; }
#chat { border: 1px solid var(--g-border) !important; border-radius: 16px !important; box-shadow: none !important; }
#msg textarea { border-radius: 24px !important; border: 1px solid var(--g-border) !important;
  padding: 12px 20px !important; font-size: 16px !important; box-shadow: none !important; }
#msg textarea:hover, #msg textarea:focus { box-shadow: 0 1px 6px rgba(32,33,36,.28) !important; border-color: transparent !important; }
#send, #clear { border-radius: 20px !important; min-width: 96px; font-weight: 500 !important; }
#send { background: var(--g-blue) !important; color: #fff !important; border: none !important; }
#clear { background: var(--g-bg) !important; color: var(--g-text) !important; border: 1px solid var(--g-bg) !important; }
#trace-title { font-size: 14px; font-weight: 500; color: var(--g-muted); margin: 4px 0 8px; }
#trace { max-height: 640px; overflow-y: auto; }
.lang { font-size: 13px; color: var(--g-text); background: #e8f0fe; border-radius: 16px; padding: 6px 12px; margin-bottom: 12px; display: inline-block; }
.trace-empty { color: var(--g-muted); padding: 24px; text-align: center; border: 1px dashed var(--g-border); border-radius: 12px; }
.card { border: 1px solid var(--g-border); border-radius: 12px; padding: 14px 16px; margin-bottom: 12px; background: #fff; }
.card-head { display: flex; gap: 10px; align-items: center; margin-bottom: 8px; }
.card .icon { font-size: 22px; background: #e8f0fe; border-radius: 50%; width: 40px; height: 40px;
  display: flex; align-items: center; justify-content: center; }
.card .step { font-size: 12px; color: var(--g-muted); }
.card .label { font-size: 15px; font-weight: 500; color: var(--g-text); }
.card .asked { font-size: 13px; color: var(--g-muted); background: var(--g-bg); border-radius: 8px; padding: 6px 10px; margin-bottom: 8px; }
.card .result p, .card .result li { font-size: 14px; color: var(--g-text); margin: 4px 0; }
.card table { width: 100%; border-collapse: collapse; font-size: 13px; margin-top: 6px; }
.card th { text-align: left; color: var(--g-muted); font-weight: 500; border-bottom: 1px solid var(--g-border); padding: 4px; }
.card td { border-bottom: 1px solid #f1f3f4; padding: 4px; vertical-align: top; }
.card .muted { color: var(--g-muted); font-size: 12px; }
.card .bad { color: #d93025; }
.card .total { font-size: 18px; font-weight: 500; color: var(--g-blue); }
"""

THEME = gr.themes.Default(
    primary_hue="blue",
    neutral_hue="gray",
    radius_size="lg",
    font=[gr.themes.GoogleFont("Roboto"), "Arial", "sans-serif"],
)

with gr.Blocks(title="Water Monkey Guesthouse", theme=THEME, css=CSS) as demo:
    gr.HTML(
        '<div id="header"><h1><span class="c1">Water</span> <span class="c2">Monkey</span> '
        '<span class="c3">Guest</span><span class="c4">house</span></h1>'
        f'<p>🐒 水猴子民宿 · Ask about rooms, prices and our rules · {escape(MODEL)}</p></div>'
    )
    with gr.Row(equal_height=False):
        with gr.Column(scale=3):
            chatbot = gr.Chatbot(type="messages", height=520, show_label=False, elem_id="chat",
                                 allow_tags=False, placeholder="Hi! I'm Little Monkey. How can I help you today?")
            box = gr.Textbox(placeholder="Ask anything about Water Monkey Guesthouse…",
                             show_label=False, elem_id="msg", lines=1)
            with gr.Row():
                send = gr.Button("Send", elem_id="send")
                clear = gr.Button("Clear", elem_id="clear")
            gr.Examples(
                ["Is there parking?", "Do you have a free room for four people?",
                 "How much is three nights in room 203?", "家庭房住兩晚多少錢？",
                 "Is there a swimming pool?", "Can you help me with my maths homework?"],
                inputs=box, label="Try asking",
            )
        with gr.Column(scale=2):
            gr.HTML('<div id="trace-title">What the assistant did (tool trace)</div>')
            trace_box = gr.HTML(EMPTY_TRACE, elem_id="trace")

    box.submit(respond, [box, chatbot], [box, chatbot, trace_box])
    send.click(respond, [box, chatbot], [box, chatbot, trace_box])
    clear.click(lambda: ([], EMPTY_TRACE), None, [chatbot, trace_box])

if __name__ == "__main__":
    demo.launch()
