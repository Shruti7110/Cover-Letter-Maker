# Cover-Letter-Maker

## 📌 Overview
It is an AI Agent designed to streamline the process of creating personalized cover letters. By leveraging user Resume details and Company Job Description, this tool generates tailored professional cover letters.

## Key Features
-  The agent extract the keywords from the Job descriptions and geneates a confidence score based on the resume. 
- It creates a structed plan on the requirements in each section.
- Based on the plan the cover letter is generated using gpt-4o-mini model.

## Step Guide
- Add your resume in the resume_description.txt file
- Copy your required job decriptions since Linkedin Scrapping is prohibited and paste it in job_description.txt
- Add your OPENAI API Key in the .env file. Ensure to remove the .example part from the file name.
- run app.py
- The cover letter will be stored in database/company_name/open_position_title/name_cover_letter.txt

## Future Scope
- Can be saved as document directly with the desired template.