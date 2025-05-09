from openai import OpenAI

client = OpenAI(
  api_key="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"
)

completion = client.chat.completions.create(
  model="gpt-4o-mini",
  store=True,
  messages=[
    {"role": "user", "content": "write a haiku about ai"}
  ]
)

print(completion.choices[0].message)
