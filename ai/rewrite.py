from openai import OpenAI

# ایجاد یک نمونه از کلاینت با کلید API خود
client = OpenAI(base_url='https://api.gapgpt.app/v1', api_key='YOUR_GAPGPT_API_KEY')

response = client.chat.completions.create(
    model="gpt-4o",
    messages=[
        {"role": "user", "content": "سلام!"}
    ]
)

print(response.choices[0].message.content)
