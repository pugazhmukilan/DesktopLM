import ollama
from tools_list import all_tools
class LLM:
    def __init__(self, model_name="llama3"):
        self.model = model_name

    def generate(self, prompt):
       
        response = ollama.chat(moddel=self.model, messages=[{'role': 'user', 'content': prompt}],tools=all_tools)
        return response["response"]
