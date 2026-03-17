import os
from openai import OpenAI

# Initialize the OpenAI client using your Azure Environment Variable
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Your core foundation. The AI compares the Job Description against this.
CANDIDATE_SUMMARY = """
Role: Technology Architect / DevOps Engineer / Cloud Infrastructure Engineer / SRE
Experience: 8+ years
Key Skills: Microsoft Azure, AWS (Amazon Web Services), CI/CD pipelines, Infrastructure as Code (Terraform, Ansible), Containerization (Docker, Kubernetes), Cloud Migrations, System Architecture, Automation.
Education: Degree in Aeronautical Engineering
"""

def evaluate_job(job_description):
    """
    Evaluates the job description against a 60-70% match threshold.
    """
    prompt = f"""
    You are an expert technical AI recruiter. Your job is to determine if a candidate should apply to a specific job opening.

    CANDIDATE BASE PROFILE:
    {CANDIDATE_SUMMARY}

    EVALUATION CRITERIA (The "60% Rule"):
    1. You must APPROVE the job if the candidate's base profile matches at least 60% to 70% of the core technical requirements.
    2. Do not look for a perfect 100% match. The candidate has an AI engine that will dynamically rewrite their resume to highlight the missing 30% using ATS optimization and JD-specific keywords. Be lenient.
    3. Acceptable roles include: DevOps Engineer, Site Reliability Engineer (SRE), Cloud Engineer, Cloud Architect, Technology Architect, Infrastructure Engineer, Platform Engineer, or Backend Automation.
    4. ONLY REJECT roles if they are completely unrelated to the candidate's ecosystem (e.g., Pure Sales, HR, Pure Frontend React/UI Developer, pure Data Scientist, or Helpdesk Support).
    
    JOB DESCRIPTION:
    {job_description[:4000]}
    
    If the job is a >= 60% match and worth generating a tailored resume for, respond with exactly and only the word: True
    If the job is completely irrelevant, respond with exactly and only the word: False
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o", # Using the flagship model for best reasoning
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1, # Keep it strictly logical
            max_tokens=5
        )
        
        result = response.choices[0].message.content.strip().lower()
        return 'true' in result
        
    except Exception as e:
        print(f"Error evaluating job: {e}")
        return False