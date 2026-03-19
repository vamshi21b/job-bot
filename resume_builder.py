import os
import uuid
import markdown
import pdfkit
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# PASTE YOUR ENTIRE 4-PAGE MASTER RESUME HERE
MASTER_PROFILE = """
Vamshi krishna Boddu
Location: Frisco, TX
vamshikrishna852@gmail.com | +1 (989)954-2212
Senior Software Engineer

PROFILE SUMMARY:

	Over 9 years of professional IT experience spanning DevOps, Site Reliability Engineering (SRE), SecOps, and System Administration, with a proven record of driving reliability and operational excellence for large-scale enterprise systems.
	Hands-on expertise in architecting and managing Azure and AWS cloud environments, specializing in secure virtual networks, scalable cloud services, load balancing, and auto-scaling.
	Serve as the essential foundation for company systems by managing cloud security, connectivity, and networking architecture across AWS and Azure platforms.
	Maintain perimeter defenses, manage infrastructure gateways, and monitor inbound and outbound internet data traffic to ensure protected access.
	Strong leadership in SRE methodologies, focusing on reducing incident frequency, automating incident response, and achieving rapid restoration of services during high-pressure production outages.
	Proficient in designing and integrating end-to-end CI/CD pipelines utilizing Jenkins, GitLab, GitHub Actions, and Azure DevOps to accelerate software delivery.
	Advanced skills in Infrastructure as Code (IaC) and configuration management using Terraform, Ansible, Chef, and Azure Resource Manager (ARM) templates.
	Extensive experience implementing robust observability, monitoring, and alerting solutions using Prometheus, Grafana, ELK, Azure Monitor, and CloudWatch to ensure proactive system health management.
	Adept at cross-functional collaboration, partnering with engineering, security, and operations teams to enforce policies via code and drive continuous improvement.
	Built and scaled back-end services in collaboration with operations and infrastructure teams, ensuring robust and efficient system functionality.
	Proactively identified and implemented changes to improve assigned codebases, product areas, and systems for scalability and maintainability.

	Operating Systems	Unix, Linux, RHEL, Ubuntu, Centos, Windows.
	Programming/scripting Languages	C++, JAVA, UNIX Shell, Bash, Perl and Python.
	Version Control Tools	Subversion, GIT Hub, GIT Swarm, GitLab
	Build Tools	MAVEN, Gradle.
	Continuous Integration Tools	Jenkins, bamboo
	AWS 	ServicesEC2, S3, EBS, VPC, ELB, AMI, SNS, RDS, IAM, Route 53, Auto scaling, Cloud Front, Cloud Watch, Cloud Trail, Cloud formation, Terraform, Security Groups, DynamoDB, Lambda, cloud patch management
	Configuration management Tools	Puppet, Chef, Ansible, ARM
	Containerization tool	Docker, Kubernetes, AKS
	Cloud infrastructure	Azure and AWS
	Project management tools	Jira, SonarQube
	Logging/Monitoring Tools	Prometheus, Grafana, cloud watch, cloud trail
	Databases and Messaging	SQL Server, MySQL, Kafka


PROFESSIONAL EXPERIENCE
Client: Infosys, Richardson, TX
Role: Technology Architect
Duration: Nov’24 - Present
Responsibilities:

	Serve as the essential foundation for company systems by managing cloud security, connectivity, and networking architecture across AWS and Azure platforms.
	Maintain perimeter defenses, manage infrastructure gateways, and monitor inbound and outbound internet data traffic to ensure protected access.
	Oversee networking architecture for Azure/AWS environments, ensuring strict perimeter defenses and managing infrastructure gateways for secure access.
	Engineered Azure Firewall instances within virtual networks to secure and tightly control inbound and outbound application traffic.
	Developed a network compliance function app utilizing Python and Azure deployment scripts to continuously monitor and enforce security policies across cloud environments.
	Partnered with security and compliance teams to harden platform components, apply automated patching, enforce policies via code, and help achieve audit and compliance requirements.
	Created and implemented Azure Resource Manager (ARM) templates and deployed them using the Azure portal and Azure PowerShell Workflow for scalable cloud infrastructure design.
	Automated repetitive operational tasks and deployment workflows using Python and PowerShell, creating reusable scripts and modules that saved engineering teams significant manual effort and reduced error rates.
	Built and managed CI/CD pipelines in GitLab, integrating automated testing, linting, container builds, and deploy stages to accelerate delivery and ensure consistent releases.
	Led the automation of incident response workflows—including runbook automation, alerting systems, and automated diagnostics—to accelerate recovery and minimize downtime during production incidents, achieving measurable reduction in P1/P2 issues.
	Experience in writing Infrastructure as a code (IAC) in Terraform, Azure resource manager (ARM), AWS Cloud formation. Created reusable Terraform modules in both Azure and AWS cloud environments.
	Engineered and maintained scalable cloud environments with a strong focus on resilience and availability, leveraging Azure Functions and automation assets to proactively resolve service bottlenecks and enhance end-user experience.
	Monitoring the DAA environment using a combination of Azure operational management service for a real time performance metrics, analyze the test results, App-Insights and alert in case of failure.
	Worked on Developing a bash scripts to update the subnets/Virtualnetworks in various aspects like service endpoints in a resource group/Subscription.
	Develop proof of concepts with the identified software tools to validate the feasibility of the technical recommendations.
	Developed security policies, standards, procedures and practices. Designed network security for DMZs and secure zones.
Environment:  Docker, Kubernetes, Ansible, Promethius, Grafana, ElasticSearch, Kibana, Git, Linux, python 3.6, Maven, Kubeflow

Client: ELXR Technologies, Plano, TX
Role: Devops Engineer
Duration: June ’21 – Oct ’24
Responsibilities:

	Developed and implemented Kubernetes manifests, helm charts for deployment of microservices into k8s clusters.
	Spearheaded the build-out of site reliability engineering (SRE) practices, focusing on system reliability, observability, incident management, and process automation for Kubernetes and Azure cloud environments.
	Led cross-functional automation initiatives and knowledge-sharing workshops to raise team capabilities in scripting, GitLab CI, cloud automation, and configuration management, increasing team productivity and deployment reliability.
	Developed and implemented Kubernetes manifests and Helm charts for the deployment of microservices into AKS clusters.
	Created and implemented Chef Cookbooks and Recipes from scratch to configure, deploy, and maintain software components, bootstrapping Chef clients remotely.
	Led the automation of incident response workflows, including runbook automation and alerting systems, to accelerate recovery and minimize downtime during production incidents.
	Worked with CI tools such as Jenkins, used Maven/Gradle to build WARs and JFrog Artifactory to manage artifacts, deploying microservices to Kubernetes clusters and application servers.
	Created Docker images by adding patches to default developer code and automated builds based on PR merges.
	Integrated SonarQube and Veracode into the release build process to perform continuous code inspection, generate unit test reports, and obtain vulnerability reports on newly pushed code.
	Engineered a distributed stream processing pipeline using Kafka and utilized Prometheus for metrics evaluation.
	Designed comprehensive monitoring solutions and incident dashboards for microservices in AKS clusters, enabling real-time detection and resolution of outages and performance degradation, with active reduction in incident rates.
	Served as the first point of escalation during production events, coordinating with engineering and infra teams to quickly restore services and perform root-cause analysis for recurring issues.
	Implemented a production ready, load balanced, highly available, fault tolerant, auto scaling Kubernetes cloud infrastructure and microservice container orchestration.
	Engineered and deployed Azure Firewall instances within a virtual network, ensuring secure, centralized control over network traffic to and from Azure applications.
	Implemented and managed firewall routing rules to direct inbound and outbound traffic through security perimeters, ensuring application protection from network-level attacks.
	Created Clusters using Kubernetes and worked on creating pods, replication controllers, replica sets, services, deployments, labels, health checks and ingress by writing Yaml files.
	Expertise in creating Docker images by adding patches to the default code written by developers by cloning default code from codebases.
	Created and Integrated SonarQube as part of the build process to check the code quality based on higher code coverage.
	Implemented SonarQube for continuous inspection of code, generate unit test reports by using Jacoco and Surefire plugins.
	Automated the Builds based on the PR merged and notify the development teams of the outcome of the builds.
	Implemented Veracode as part of the release build process to get the vulnerability report on the new code pushed.
Environment: Docker, Kubernetes, Ansible, Jenkins, Prometheus, Grafana, ElasticSearch, Kibana, Git, Linux, python 3.6, Maven, Kubeflow

Client: Thinklusive, New Jersey
Role: Devops Engineer
Duration: Sept ’19 – May ’21
Responsibilities:

	Built, implemented, and maintained Infrastructure as code utilizing Terraform modules for application deployment across multiple cloud providers.
	Configured Ansible and Ansible Tower as configuration management tools to automate repetitive tasks, deploy applications, manage changes, and verify functionality.
	Managed Ansible Playbooks with Ansible roles and created dynamic inventories for automating continuous deployment pipelines.
	Configured and integrated Git into the continuous integration environment alongside Jenkins, writing scripts to containerize applications using Ansible with Docker and orchestrating via Kubernetes.
	Created virtual machines, templates, clones, and snapshots, deploying Red Hat enterprise machines out of templates and clones.
	Monitored system performance and executed kernel tuning to significantly enhance overall system performance.
	Build, manage, and continuously improve infrastructure for global software development engineering teams including implementation of build scripts, continuous integration infrastructure and deployment tools. 
	Implemented Kubernetes to deploy scale, load balance, scale and manage docker containers with multiple name spaced versions.
	Provided regular support guidance to Splunk project teams on complex solution and issue resolution.
	Hands on experience in installing creating and configuring Kubernetes and troubleshooting kube API, pods, Kubelet, kube-proxy, controller, scheduler and ETCD.

Client: Visam Technologies, Hyderabad
Role: Linux Administrator
Duration: Mar’16 – Aug’19
Responsibilities:

	Installation and troubleshooting on VMware running Linux (Red Hat) and Windows.
	Creating VM's, templates, clones, snapshots and deploying Red hat enterprise machines out of templates and clones.
	Installation, Configuration & Upgrade of operating systems Linux on Windows hardware.
	Monitoring System performance and do kernel tuning to enhance the system Performance, worked on installation, configuration and maintenance of Debian/Red hat, CentOS Servers at multiple Data Centres.
	Responsible for helping spin up and maintain RHEL EC2 instances and AWS security groups, RDS Instances.
	Managed AWS IAM roles and policies in support of Instances accessibility to the users.
	Ability to work with administrators from troubleshooting complex system issues, experiences on AWS(EC2, S3, EBS).
	Management of Red Hat Linux user accounts, groups, active directories, and file permissions.
	Monitoring system resources, logs, disk usage, scheduling backups and restore.
	Configured auto mounts/maps for the user accounts.
	Installation, Configuration of Web Servers using Apache, IIS on Solaris, and NT Servers.
	Configuration and Clustering of Managed Servers.

Education details:

	Bachelor’s – VNR Vignana Jyothi Institute of Engineering and Technology – Information Technology – 2018
	Master’s – Central Michigan University – Information Systems - 2021

"""

def generate_tailored_resume(job_description):
    print("-> 🧠 AI is crafting a comprehensive, multi-page bespoke resume...")
    
    prompt = f"""
    You are an elite executive ATS resume optimizer. 
    I will provide my comprehensive Master Profile, and the Job Description for a role I am targeting.
    
    Your task:
    1. Maintain the FULL LENGTH and comprehensive detail of the original Master Profile. DO NOT truncate, summarize, or cut sections to fit 1 page. The final output must be as large as the input.
    2. Seamlessly weave exact keywords and technical requirements from the Job Description into the Professional Summary and Experience bullet points.
    3. Add 2 to 3 highly specific, ATS-optimized bullet points relevant to the job description, ensuring they logically align with my existing experience. Do not hallucinate core skills I do not possess.
    4. Format the output STRICTLY in clean Markdown (use # for Name, ## for sections, and bullet points). Do not include any conversational filler.
    
    MASTER PROFILE:
    {MASTER_PROFILE}
    
    JOB DESCRIPTION:
    {job_description[:4000]}
    """
    
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3
    )
    
    resume_markdown = response.choices[0].message.content
    resume_markdown = resume_markdown.replace("```markdown", "").replace("```", "").strip()
    
    html_content = markdown.markdown(resume_markdown)
    
    # Updated CSS for multi-page rendering
    styled_html = f"""
    <html>
    <head>
        <style>
            body {{ font-family: 'Arial', sans-serif; font-size: 12px; line-height: 1.5; color: #333; margin: 40px; }}
            h1 {{ font-size: 22px; color: #000; text-transform: uppercase; margin-bottom: 5px; text-align: center; }}
            h2 {{ font-size: 16px; border-bottom: 1px solid #000; padding-bottom: 2px; margin-top: 20px; color: #222; page-break-after: avoid; }}
            p {{ margin-bottom: 8px; }}
            ul {{ margin-top: 5px; padding-left: 20px; }}
            li {{ margin-bottom: 6px; }}
        </style>
    </head>
    <body>
        {html_content}
    </body>
    </html>
    """
    
    pdf_filename = f"/tmp/tailored_resume_{uuid.uuid4().hex[:8]}.pdf"
    
    options = {
        'page-size': 'Letter',
        'margin-top': '0.75in',
        'margin-right': '0.75in',
        'margin-bottom': '0.75in',
        'margin-left': '0.75in',
        'encoding': "UTF-8",
        'quiet': ''
    }
    
    pdfkit.from_string(styled_html, pdf_filename, options=options)
    print(f"-> 📄 Tailored PDF generated: {pdf_filename}")
    
    return pdf_filename