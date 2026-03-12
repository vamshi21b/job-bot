import os
from openai import OpenAI

# Initialize the client securely
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def evaluate_job(description_text):
    """
    Passes the job description to OpenAI. 
    Returns True if it's a match, False if we should skip it.
    """
    
    system_prompt = """
    You are an expert technical recruiter evaluating job descriptions for a Senior DevOps Engineer and Technology Architect.
    
    Your candidate's core stack is: Azure, AWS, Site Reliability Engineering (SRE), Terraform, and Ansible.
    
    Read the provided job description and reply with EXACTLY 'YES' or 'NO' based on these strict rules:
    
    1. MATCHING TECH: The role MUST heavily feature either Azure or AWS, alongside IaC tools like Terraform or Ansible.
    2. SENIORITY: Reject junior, entry-level, or basic sysadmin roles. It must be Architect, Lead, or Senior DevOps level.
    3. EXCLUSIONS: Reply 'NO' if the job requires heavy software development (e.g., full-stack Java/C# coding) rather than infrastructure and pipeline architecture.
    4. CLEARANCES: Reply 'NO' if the job explicitly requires an active Top Secret or DoD security clearance.
    
    If the job meets the criteria, reply YES. Otherwise, reply NO. Do not explain your reasoning.
    """

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo", # or gpt-4o-mini for better reasoning at a low cost
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Job Description:\n{description_text}"}
            ],
            temperature=0.1, # Keep it deterministic and strict
            max_tokens=5
        )
        
        # Clean up the response and check if the AI said YES
        decision = response.choices[0].message.content.strip().upper()
        return "YES" in decision
        
    except Exception as e:
        print(f"OpenAI API Error: {e}")
        return False