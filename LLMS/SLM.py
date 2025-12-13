import ollama
from langchain_core.prompts import PromptTemplate
import json
from sys_prompt_slm import SYSTEM_PROMPT
import sys
import os
import json
import dotenv
import google.generativeai as genai


sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from tools.data import get_curr_date_time
dotenv.load_dotenv()

google_api = os.getenv("GOOGLE_API_KEY")
genai.configure(api_key=google_api)


class SLM:
    def __init__(self, model_name="qwen2.5:3b"):
        self.model = model_name
        self.system_prompt = SYSTEM_PROMPT

    def generate(self, user_input):
       
        messages = [
            {
                "role": "system",
                "content": self.system_prompt
            },
            {
                "role": "user",
                "content": user_input
            }
        ]

        response = ollama.chat(
            model=self.model,
            messages=messages,
            format="json",  # IMPORTANT: forces JSON output
            tools = [get_curr_date_time]
        )

        return json.loads(response["message"]["content"])



class googleSLM():
    def __init__(self,systemprompt):
        self.system_prompt = systemprompt
    def generate(self,user_input):


        message = [{
                "role": "system",
                "content": self.system_prompt
            },
            {
                "role": "user",
                "content": user_input
            }
            ]
        
        model = genai.GenerativeModel(
            model_name="gemini-2.0-flash",
            system_instruction=self.system_prompt,
            tools = [get_curr_date_time])
        response= model.generate_content(user_input)
        return  response
    



if __name__ == "__main__":
    slm = SLM()
    prompt = """Honestly today was exhausting.

College work just keeps piling up and I feel like I barely have time to breathe.
Anyway, that’s just me venting.

I think I have an important meeting tomorrow at 4 PM with my project guide,
I really don’t want to miss that because last time it became a problem.

Also, I told my teammate that I’ll help him debug his code tomorrow evening.

By the way, I’ve noticed that when explanations are too long, I kind of zone out.
Short and clear explanations work much better for me.

Here is a long article I copied from the internet, can you explain it to me?

The man Elon Musk fired from Twitter in a single day…
built a new AI powerhouse and made a huge comeback.
A job can be taken away — but not your vision.

Parag Agrawal — the IIT-Bombay and Stanford-educated tech leader — was appointed CEO of Twitter in November 2021, succeeding Jack Dorsey. But shortly after Elon Musk acquired Twitter (now X) in October 2022, Musk fired Parag within hours of taking control.  

Instead of fading away, Parag took a brave step forward.

He founded an AI startup called Parallel Web Systems in 2023 — a company that builds tools to help AI systems research the internet more like a human would.  

In just two years, Parag’s new venture has:

💡 Raised major funding (about $30M+) from top investors including Khosla Ventures, First Round Capital, and Index Ventures.  
💡 Built AI technology used daily for millions of research tasks.  
💡 Positioned itself as a key enabler for the next generation of AI agents — the tools that will power tomorrow’s automated assistants and intelligent systems.  

🔹 AI Startup — Parallel Web Systems
After Twitter, Agrawal founded an AI infrastructure company called Parallel Web Systems.
The startup focuses on building web infrastructure and APIs that allow AI agents to interact with the live web — letting AI systems fetch, verify, and synthesise up-to-date web data for tasks like research, coding, analytics, and enterprise workflows.
📊 Funding & Valuation
Parallel Web Systems recently completed a Series A funding round, raising $100 million.
The company’s valuation after this round is approximately $740 million-₹6,653 Crores (post-money).
The round was co-led by major venture firms including Kleiner Perkins and Index Ventures, with participation from Khosla Ventures and other existing investors. 
🔍 What the Company Does
Its platform offers tools like a deep research API and multiple specialized AI research engines. These let AI applications perform real-time internet research with accurate citations — an advancement beyond static model training data. LinkedIn
Parallel’s tech helps enterprise customers power AI agents for tasks such as software development, data analysis, and risk assessment workflows

Parag didn’t just bounce back — he redefined his path from tech executive to AI pioneer.

The lesson?
A job title can disappear.
But skills, ideas, and resilience never can.

Lose a role — gain a mission.
Lose a job — find your breakthrough.

Sorry for dumping everything at once.
"""
    print(slm.generate(prompt))
    print(slm.generate("i always get cold when i to chalk crafting and chalk carving"))