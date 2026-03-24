import os
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

CANDIDATE_SUMMARY = """
Role: Technology Architect / DevOps Engineer / Cloud Infrastructure Engineer / SRE
Experience: 9+ years
Key Skills: Microsoft Azure, AWS (Amazon Web Services), CI/CD pipelines, Infrastructure as Code (Terraform, Ansible), Containerization (Docker, Kubernetes), Cloud Migrations, System Architecture, Automation.
Education: Degree in Aeronautical Engineering, Master's in Information Systems
"""

def evaluate_job(job_description):
    prompt = f"""
    You are an expert technical AI recruiter. Determine if the candidate should apply to this job.

    CANDIDATE BASE PROFILE:
    {CANDIDATE_SUMMARY}

    EVALUATION CRITERIA:
    1. APPROVE the job if the candidate's base profile matches at least 60% of the core technical requirements.
    2. Do not look for a perfect match. The candidate has an AI engine that will dynamically rewrite their resume to inject the missing 40-50% of keywords and experience. Be highly lenient.
    3. Acceptable roles include: DevOps, SRE, Cloud Engineer, Cloud Architect, Technology Architect, Infrastructure Engineer, or Platform Engineer.
    4. ONLY REJECT roles if they are completely unrelated (e.g., Pure Sales, HR, pure Data Scientist, Helpdesk).
    
    JOB DESCRIPTION:
    {job_description[:4000]}
    
    If the job is a >= 60% match, respond with exactly: True
    If completely irrelevant, respond with exactly: False
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=5
        )
        return 'true' in response.choices[0].message.content.strip().lower()
    except Exception as e:
        print(f"Error evaluating job: {e}")
        return False