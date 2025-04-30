from typing import List, Dict
from pydantic import BaseModel, Field
from openai import OpenAI
import os
import logging

# Set up logging configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
model = "gpt-4o-mini"

JD_file_path = "database/job_description.txt"  # replace with your actual file path
resume_file_path = "database/resume_description.txt"  # replace with your actual file path

# --------------------------------------------------------------------
# Step 1: Define the data models
# ---------------------------------------------------------------


class SubTask(BaseModel):
    """Letter section task defined by orchestrator"""

    section_type: str = Field(description="Type of letter section to write")
    description: str = Field(description="What this section should cover")
    style_guide: str = Field(description="Writing style for this section")
    target_length: int = Field(description="Target word count for this section")


class OrchestratorPlan(BaseModel):
    """Orchestrator's letter structure and tasks"""
    company_name: str = Field(description="Company name for the letter")
    company_industry: str = Field(description="Company industry for the letter")
    job_description: str = Field(description="Company job description")
    job_title: str = Field(description="Job title for the letter")
    job_description_analysis: str = Field(
        description="Analysis of the company job description"
    )
    job_description_keywords: List[str] = Field(
        description="Keywords from the job description upto maximum 15"
    )
    sections: List[SubTask] = Field(description="List of sections to write")

    def compute_cv_match_score(self, cv_text: str) -> float:
        """Compute how well the CV matches job keywords"""
        matches = [
            kw for kw in self.job_description_keywords if kw.lower() in cv_text.lower()
        ]
        return (
            round(len(matches) / len(self.job_description_keywords), 4)
            if self.job_description_keywords
            else 0.0
        )
    def missing_keywords(self, cv_text: str) -> List[str]:
        """Compute missing keywords from the CV"""
        return [
            kw for kw in self.job_description_keywords if kw.lower() not in cv_text.lower()
        ]


class SectionContent(BaseModel):
    """Content written based on each section Description"""

    content: str = Field(description="Written content for the section")
    key_points: List[str] = Field(description="Main points covered")

class Resume(BaseModel):
    """Resume or CV of the candidate"""

    name: str = Field(description="Candidate's name")
    contact_info: str = Field(description="Candidate's contact information")
    education: List[str] = Field(description="Candidate's education history")
    work_experience: List[str] = Field(
        description="Candidate's work experience and achievements"
    )
    skills: List[str] = Field(description="Candidate's skills and certifications")
    projects: List[str] = Field(description="Candidate's projects and contributions") 
    certifications: List[str] = Field(description="Candidate's certifications")
    extra_curricular: List[str] = Field(description="Candidate's extra-curricular activities")

# --------------------------------------------------------------
# Step 2: Define prompts
# --------------------------------------------------------------

COVER_LETTER_PROMPT = """
You are an AI assistant that generates personalized, professional cover letters tailored to specific job descriptions and candidate resumes.

### You will be given:
- A job description (JD)
- A candidate's resume or CV
- Target length for the cover letter

Your task:
1. Understand the role, responsibilities, and required skills from the job description.
2. Read the candidate’s resume and identify relevant experiences, skills, and achievements.
3. Generate a cover letter that:
   - Is no more than 3 paragraphs long
   - Sounds confident, clear, and tailored to the role
   - Emphasizes the candidate’s alignment with the company’s goals and culture
   - Is free of generic or repetitive language


### Sample Cover Letter (for reference):

Dear Hiring Manager,

I am writing to express my strong interest in the AI/ML - Computer Vision Engineer role at HARMAN. With a B.Tech in Instrumentation and Control Engineering and hands-on experience in AI/ML, Computer Vision, Embedded Systems, and Signal Processing, I bring a unique interdisciplinary edge critical for this position.

I am particularly interested in the opportunity to work on computer vision, sensor handling, and simulation tasks. My background aligns with these areas, and I am enthusiastic about applying my skills to develop innovative solutions.

In my role as an Electrical Engineer at Baxter International, I have gained experience on working on multiple field issues to deal with real time problems and finding robust solutions. This has enhanced my problem-solving skills and adaptability. Worked on digital electronic design and various analysis methods, along with POCs like Hardware-in-loop, Motor Predictive maintenance, and Sensor Dashboard.

I have developed projects such as a brain tumor detection system utilizing YOLOv10 and an AI-powered event planner chatbot integrating LangChain and OpenAI GPT. These experiences have provided me with proficiency in Python, machine learning frameworks like TensorFlow and PyTorch, and an understanding of computer vision and control systems. Beyond this, I have done multiple end-to-end projects to enhance my skills in AI which gave me great understanding in LLMs, NLP, RLHF, Processing & handling data, finetuning models, creating AI agents and much more.

I am highly self-driven, adaptable, and passionate about creating robust, scalable AI solutions that drive innovation — traits that fit HARMAN’s agile and cutting-edge culture. I am eager to contribute my skills towards enhancing HARMAN’s 3D computer vision and Augmented Reality solutions.

Thank you for considering my application. I am excited about the possibility of joining HARMAN and would welcome the opportunity to discuss how my background can contribute to your team.

Warm Regards,
Shruti Pawar

### Format your response as follows:
---

**Dear [Hiring Manager/Company Name],**

**[Paragraph 1]** – Introduce the candidate and mention the role they’re applying for. Include 1-2 lines on why they’re excited about the opportunity or the company.

**[Paragraph 2]** – Summarize 2–3 key qualifications or achievements from the resume that aligndirectly with the job requirements. Use specific metrics or impact where possible. Add my work experience that aligns to the interest of the company. This is a good place to mention any relevant projects or experiences that demonstrate the candidate's fit for the role.

**[Paragraph 3]** - Add projects i have worked on a which are aligned with the job description. Highlight any relevant skills, tools, or technologies that are mentioned in the JD. This is a good place to mention soft skills or cultural fit. Add 2 projects maximum.

**[Paragraph 4]** – Close with a confident statement of interest, willingness to contribute, and a call to action (e.g., looking forward to discussing further).

**Thanks & Regards,\n
    Shruti Pawar**

---

### Rules:
- Never make up experiences that aren’t in the resume.
- Do not exceed 3 paragraphs.
- Tailor tone slightly based on the company's industry (formal for finance, warm for startups, etc.)
- Keep it professional, enthusiastic, and to the point.

"""

# --------------------------------------------------------------
# Step 3: Implement orchestrator
# --------------------------------------------------------------
    
class CVOrchestrator:
    def __init__(self):
        self.sections_content = {}     # Store the content of each section    
    
    def get_resume(self, file_path: str):
        with open(file_path, "r", encoding="utf-8") as f:
            resume_text = f.read()
        return resume_text
    
    def read_resume(self, file_path: str) -> Resume:
        """Read the resume file and return a Resume object"""
        with open(file_path, "r", encoding="utf-8") as f:
            resume_data = f.read()
        completion = client.beta.chat.completions.parse(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content":  f"Extract the resume information from the following text: {resume_data}"
                }
            ],
            response_format=Resume,
        )
        return completion.choices[0].message.parsed
        
    def get_plan(self, file_path: str, target_length: int) -> OrchestratorPlan:
        """Get orchestrator's cover letter structure plan"""
        logger.info("Reading through the job description")
        with open(file_path, "r", encoding="utf-8") as f:
            job_description = f.read()
        
        completion = client.beta.chat.completions.parse(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": f"The {job_description} file has data for company to apply. Extract information from the job description data "
                            f"Do not use the details from sample cover letter. It is only to understand the format and style of writing. "
                            f"Add the Thanks and Regards Section with my name: {resume_data.name} at the end of the letter."
                            f"{COVER_LETTER_PROMPT.format(job_description=job_description, target_length=target_length)}"
                    
                }
            ],
            response_format=OrchestratorPlan,
        )
        return completion.choices[0].message.parsed
    
    def save_other_details(self, file_path: str):
        logger.info("Saving all the details to a Markdown file")
        """Save job description analysis and resume match score to a Markdown file"""
        score = plan.compute_cv_match_score(resume_text)
        text = (
            f"# 🔍 CV Keyword Match Summary\n\n"
            f"**✅ Missing keywords from the CV:** `{plan.missing_keywords(resume_text)}`\n\n"
            f"**📊 CV matched:** **{score * 100:.2f}%** of job description keywords.\n\n"
            f"---\n\n"
            f"## 🏢 Job Details\n\n"
            f"**Company Name:** {plan.company_name}\n\n"
            f"**Job Title:** {plan.job_title}\n\n"
            f"**Industry:** {plan.company_industry}\n\n"
            f"**Job Description:**\n{plan.job_description}\n\n"
            f"**Job Description Analysis:**\n{plan.job_description_analysis}\n\n"
            f"**Extracted Keywords:** `{', '.join(plan.job_description_keywords)}`\n\n"
            f"---\n\n"
            f"## 📄 Cover Letter Sections\n\n"
            f"```json\n{plan.sections}\n```\n\n"
            f"---\n\n"
            f"## 🙋‍♀️ Resume Summary\n\n"
            f"**Name & Contact:** {resume_data.name} - {resume_data.contact_info}\n\n"
            f"### 💼 Work Experience\n{resume_data.work_experience}\n\n"
            f"### 🛠️ Skills\n{resume_data.skills}\n\n"
            f"### 🚀 Projects\n{resume_data.projects}\n\n"
            f"### 🎓 Certifications\n{resume_data.certifications}\n\n"
            f"### 🎯 Extra Curricular Activities\n{resume_data.extra_curricular}\n\n"
        )

        # Create directories if they don't exist
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        # Save the text to a Markdown file
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(text)
    
    def write_sections(self, sections: List[SubTask], resume_text: str) -> List[SectionContent]:
        """Write the cover letter"""
        logger.info("Writing each section of the cover letter")
        previous_sections_text = ""
        section_contents = []
        user_prompt_common =  (f"for required resume details use: {resume_data}"
                    f"Do not repeat the same information in the next section."
                    f"Make sure to include the following keywords: {plan.job_description_keywords}"
                    f"Ensure format is not very different from Sample Cover Letter provided in the prompt {COVER_LETTER_PROMPT}. "
                    f"Do not add false information or make up experiences that aren not in the resume: {resume_data}."
                    f"Do not include electric engineer just my company name and any work experience that aligns to the interest of the company."
                    f"Add Thanks and Regards at the end of the letter with my name: {resume_data.name} on the next line."
                    )
        for section in sections:
            if previous_sections_text:
                user_prompt_common += (
                f"\nRefer to the previous sections written so far for context:\n{previous_sections_text}"
                )
            completion = client.beta.chat.completions.parse(        
                model=model,
                messages=[
                    {
                    "role": "user",
                    "content": f"{user_prompt_common} "
                                f"Write a {section.section_type} for the cover letter based on the following description: {section.description}"
                                f" and style guide: {section.style_guide}. The target length is {section.target_length} words."
                    }
                ],
                response_format=SectionContent,
            )
            parsed_section = completion.choices[0].message.parsed
            section_contents.append(parsed_section)
            previous_sections_text += f"\n\n=== {section.section_type} ===\n{parsed_section.content}"

        return section_contents
    
    def save_letter(self, file_path: str, sections: List[SectionContent]):
        """Save the cover letter to a file"""
        logger.info("Saving the cover letter to a file")
        with open(file_path, "w", encoding="utf-8") as f:
            for section in sections:
                f.write(section.content + "\n\n")


if __name__ == "__main__":
    orchestrator = CVOrchestrator()
    resume_text = orchestrator.get_resume(resume_file_path) # get resume as text
    resume_data  = orchestrator.read_resume(resume_file_path) #read resume in a structured format using tools
    plan = orchestrator.get_plan(JD_file_path, 1000) #save the Job description in a structured format using tools and get the plan
    orchestrator.save_other_details(f"database/{plan.company_name}/{plan.job_title}/other_details.md") #save all the details to a markdown file
    section = orchestrator.write_sections(plan.sections, resume_text) #write the sections of the cover letter using tools
    orchestrator.save_letter(f"database/{plan.company_name}/{plan.job_title}/Shruti_Pawar_Cover_Letter.txt", section) #save the cover letter to a file
    print("Cover letter generated and saved successfully!")