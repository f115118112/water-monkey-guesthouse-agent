"""Gradio chat screen for Water Monkey Guesthouse.

Run:  python app.py   then open the link it prints (usually http://127.0.0.1:7860).
"""

import json

import gradio as gr

from agent import MODEL, make_client, run_agent

client = make_client()


def format_trace(trace):
    if not trace:
        return "_No tool was called for this message._"
    lines = []
    for i, step in enumerate(trace, 1):
        args = json.dumps(step["args"], ensure_ascii=False)
        result = json.dumps(step["result"], ensure_ascii=False, indent=2)
        lines.append(f"**{i}. `{step['tool']}`**\n\nArguments: `{args}`\n\nResult:\n```json\n{result}\n```")
    return "\n\n---\n\n".join(lines)


def respond(user_message, history):
    if not user_message.strip():
        return "", history, gr.update()
    reply, trace = run_agent(client, history, user_message)
    history = history + [
        {"role": "user", "content": user_message},
        {"role": "assistant", "content": reply},
    ]
    return "", history, format_trace(trace)


with gr.Blocks(title="Water Monkey Guesthouse") as demo:
    gr.Markdown(f"# 🐒 Water Monkey Guesthouse 水猴子民宿\nAsk about rooms, prices and our rules. Model: `{MODEL}`")
    with gr.Row():
        with gr.Column(scale=3):
            chatbot = gr.Chatbot(type="messages", height=500, label="Chat")
            box = gr.Textbox(placeholder="e.g. How much is three nights in room 203?", label="Your message")
            with gr.Row():
                send = gr.Button("Send", variant="primary")
                clear = gr.Button("Clear")
            gr.Examples(
                ["Is there parking?", "Do you have a free room for four people?",
                 "How much is three nights in room 203?", "家庭房住兩晚多少錢？",
                 "Is there a swimming pool?", "Can you help me with my maths homework?"],
                inputs=box,
            )
        with gr.Column(scale=2):
            trace_box = gr.Markdown("_The tool trace will show here._", label="Tool trace")

    box.submit(respond, [box, chatbot], [box, chatbot, trace_box])
    send.click(respond, [box, chatbot], [box, chatbot, trace_box])
    clear.click(lambda: ([], "_The tool trace will show here._"), None, [chatbot, trace_box])

if __name__ == "__main__":
    demo.launch()
