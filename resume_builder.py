import os
import uuid
import markdown
import pdfkit
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Your Immutable Master Profile
# This is the bedrock of your experience. The AI will pull from this, but never invent new jobs.
MASTER_PROFILE = """
Name: Vamshi Krishna Boddu
Location: Frisco, TX
Contact: vamshikrishna852@gmail.com | 989-954-2212 | https://linkedin.com/in/vamshikrishnaboddu
Education: Degree in Aeronautical Engineering

Current Role: Technology Architect & DevOps Engineer
Company: Infosys
Experience Focus: 8+ years of enterprise architecture and DevOps engineering.
Core Stack: Microsoft Azure, AWS (Amazon Web Services), CI/CD pipelines, Infrastructure as Code, Cloud Migrations, Containerization.

Professional Summary:
A highly skilled Technology Architect and DevOps Engineer specializing in designing, deploying, and optimizing scalable cloud infrastructure across Azure and AWS environments. Proven track record in bridging the gap between development and operations to accelerate delivery lifecycles.

Key Projects & Skills:
- Architected and maintained secure, highly available cloud infrastructures.
- Spearheaded DevOps transformations utilizing modern CI/CD principles.
- Expert in automating deployments and managing infrastructure state.
"""

def generate_tailored_resume(job_description):
    print("-> 🧠 AI is crafting a bespoke resume for this specific role...")
    
    prompt = f"""
    You are an elite executive resume writer. 
    I will provide my Master Profile, and the Job Description for a role I am applying for.
    
    Your task:
    1. Write a 1-page, highly professional, ATS-optimized resume.
    2. STRICT RULE: You may NOT invent or hallucinate any experience, companies, or degrees not present in the Master Profile.
    3. Tailor the Professional Summary and the emphasis of the bullet points to perfectly align with the keywords and core requirements of the Job Description. 
    4. Format the output STRICTLY in clean Markdown (use # for Name, ## for sections, and bullet points). Do not include any conversational filler.
    
    MASTER PROFILE:
    {MASTER_PROFILE}
    
    JOB DESCRIPTION:
    {job_description[:4000]}
    """
    
    response = client.chat.completions.create(
        model="gpt-4o", # Ensure you are using 4o or 4-turbo for high reasoning
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3
    )
    
    resume_markdown = response.choices[0].message.content
    
    # Clean up any potential markdown code blocks
    resume_markdown = resume_markdown.replace("```markdown", "").replace("```", "").strip()
    
    # 2. Convert Markdown to clean, ATS-friendly HTML
    html_content = markdown.markdown(resume_markdown)
    
    # Inject basic CSS to ensure the PDF looks professional and fits on one page
    styled_html = f"""
    <html>
    <head>
        <style>
            body {{ font-family: 'Arial', sans-serif; font-size: 11px; line-height: 1.4; color: #333; margin: 30px; }}
            h1 {{ font-size: 20px; color: #000; text-transform: uppercase; margin-bottom: 5px; text-align: center; }}
            h2 {{ font-size: 14px; border-bottom: 1px solid #000; padding-bottom: 2px; margin-top: 15px; color: #222; }}
            p {{ margin-bottom: 5px; }}
            ul {{ margin-top: 5px; padding-left: 20px; }}
            li {{ margin-bottom: 4px; }}
            .contact-info {{ text-align: center; font-size: 10px; margin-bottom: 15px; }}
        </style>
    </head>
    <body>
        {html_content}
    </body>
    </html>
    """
    
    # 3. Compile HTML to PDF
    pdf_filename = f"/tmp/tailored_resume_{uuid.uuid4().hex[:8]}.pdf"
    
    options = {
        'page-size': 'Letter',
        'margin-top': '0.5in',
        'margin-right': '0.5in',
        'margin-bottom': '0.5in',
        'margin-left': '0.5in',
        'encoding': "UTF-8",
        'quiet': ''
    }
    
    pdfkit.from_string(styled_html, pdf_filename, options=options)
    print(f"-> 📄 Tailored PDF generated: {pdf_filename}")
    
    return pdf_filename