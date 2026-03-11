import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def evaluate_job(job_description):
    """Evaluates the JD against your DevOps profile using the mini model."""
    
    system_prompt = """
    You are an AI assistant helping a candidate apply for DevOps roles. 
    The candidate has strong experience in Azure, Python, and building automated 
    network compliance function apps. 
    
    Analyze the provided job description. 
    1. Return 'MATCH' if the role is a good fit for an Azure/Python DevOps Engineer.
    2. Return 'SKIP' if it heavily requires unrelated skills.
    3. If 'MATCH', provide a 2-sentence cover letter snippet highlighting their 
       Python network compliance automation and Azure deployment experience.
       
    Format: [MATCH/SKIP] | [Snippet]
    """

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": job_description}
        ],
        temperature=0.2
    )
    
    return response.choices[0].message.content