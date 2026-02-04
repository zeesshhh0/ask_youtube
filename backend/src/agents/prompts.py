from langsmith import Client

client = Client()
ask_youtube_agent_system_prompt = client.pull_prompt(
    "ask_youtube_agent_system_prompt",
)