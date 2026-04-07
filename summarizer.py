import io
import fitz
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from google import genai
import db

def extract_text_from_pdf(pdf_url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/pdf'
    }
    try:
        resp = requests.get(pdf_url, headers=headers, stream=True, timeout=15)
        resp.raise_for_status()
        pdf_bytes = resp.content
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        text = ""
        for page in doc:
            text += page.get_text() + "\n"
        return text
    except Exception as e:
        print(f"Failed to download/parse PDF: {e}")
        return None

def generate_summary(circular_id, api_key):
    circular = None
    circs = db.get_all_circulars()
    for c in circs:
        if c['id'] == circular_id:
            circular = c
            break
            
    if not circular:
        return "Circular not found in Database."
        
    if circular['summary']:
        return circular['summary']

    print(f"Extracting PDF text for {circular['title']} ...")
    actual_pdf_url = circular['pdf_url']
    if "file=" in actual_pdf_url:
        actual_pdf_url = actual_pdf_url.split("file=")[-1]
        
    if actual_pdf_url.endswith(".html"):
        from scraper import init_driver
        driver = init_driver()
        try:
            driver.get(actual_pdf_url)
            iframe = WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.XPATH, "//iframe")))
            src = iframe.get_attribute("src")
            if src and "file=" in src.lower():
                actual_pdf_url = src.split("file=")[-1]
        except:
            pass
        finally:
            driver.quit()
            
    if not actual_pdf_url.lower().endswith(".pdf"):
        return f"Error: Could not extract valid PDF link from {circular['pdf_url']}. Make sure the Circular has an attached document."

    text = extract_text_from_pdf(actual_pdf_url)
    if not text:
        return f"Could not extract text from {actual_pdf_url}"
        
    print("Calling Gemini API...")
    
    if circular.get('category') == 'SEBI Circulars':
        full_prompt = get_circular_prompt(text)
    else:
        full_prompt = get_analyst_prompt(text)
    
    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=full_prompt,
        )
        summary = response.text
        db.save_summary(circular_id, summary)
        return summary
    except Exception as e:
        print(f"Gemini API Error: {e}")
        return f"Error connecting to Gemini API: {e}"

def get_analyst_prompt(circular_text):
    return f""" You are a financial regulatory analyst with expertise in SEBI regulations, securities law, and capital-market policy.
The user will provide the extracted text of a SEBI Consultation Paper or Draft Circular.
Your task is to produce a structured review document in the format used by legal policy and market-regulation think tanks.

The output must follow the structure and depth below. Write in a formal, analytical, and neutral tone, formatted cleanly for Word/Markdown export.

🔹 STRUCTURE AND GUIDELINES
Market Classification

Classify the consultation paper under one of the following divisions based on subject matter:

Primary Markets – IPOs, FPOs, REITs, InvITs, public issues, and capital formation.

Secondary Markets – Trading, exchanges, market intermediaries, surveillance, disclosures, and investor protection.

Commodity Markets – Regulation of commodity exchanges and derivatives.

External Markets – Cross-border listings, foreign portfolio investment, GDRs, ADRs, or external capital flows.

Output at the top:
Market Classification: [Primary / Secondary / Commodity / External]

1. Background / Regulatory Context / Introduction

Include:

A clear overview of what the Consultation Paper is about.

The existing regulatory framework under SEBI Regulations, circulars, or Master Circulars.

The evolution and pain points that triggered SEBI’s reform initiative.

Any relevant legislative or circular history, including important amendment dates or regulations.

Purpose of the proposed reform in one or two sentences.

2. Summary of Key Proposals

Provide a neutral summary of what SEBI has proposed — without opinion or interpretation.

Use bullet points or short paragraphs for clarity.

Mention each proposal separately as it appears in the Consultation Paper (e.g., Proposal 1, Proposal 2, etc.).

Avoid legal commentary here — keep it descriptive.

3. Critical Analysis of the Proposals

This is the analytical core of the review.
For each distinct proposal, use the sub-structure below:

Proposal [Number]: [Title of Proposal from CP]

Concept Proposed:
Provide a neutral summary of what SEBI is proposing in this section — exactly as per the Consultation Paper.

SEBI’s Rationale:
Summarize SEBI’s policy reasoning or intent behind the proposal — why it is needed, what problem it solves, and what benefits it seeks to bring.

Global Benchmarking:
Compare this proposal with how similar regulatory issues are handled in three to four relevant international jurisdictions (select from: US SEC, UK FCA, EU ESMA, Singapore MAS, Hong Kong SFC/HKEX).

Identify comparable frameworks or approaches in these countries.

Discuss whether India’s proposal aligns or diverges from them.

Provide references or URLs only for this subsection (e.g., links to regulator websites or policy documents).

Critical Assessment & Recommendations:

Our Stance:
State the team’s position – Accepted / Accepted with Modifications / Not Accepted.

Supporting Rationale:
Provide detailed justification for the stance. Explain the potential regulatory, legal, or market impact (positive or negative).

Proposed Modifications / Safeguards (if applicable):
If accepted with modification, propose specific, actionable alternatives, such as:

Revised thresholds or timelines

Additional disclosure requirements

Transitional or phased implementation clauses

Anti-avoidance or investor-protection safeguards

4. Conclusion and Overall Recommendations

Summarize:

Whether SEBI’s approach is conceptually sound and internationally aligned.

The overall impact on market efficiency, investor protection, and regulatory coherence.

Provide 3–5 overall recommendations on how SEBI could refine or clarify its proposals before finalizing the framework.

Use bullet points for clarity and conciseness.

5. Key Questions for the Ministry of Finance (MoF)

List five critical questions that the Ministry of Finance should ask SEBI about this Consultation Paper.
These should be policy-oriented, forward-looking, and designed to:

Challenge underlying assumptions,

Strengthen implementation logic, or

Enhance alignment with India’s market-development objectives.

DO NOT MISS ANY "PROPOSAL". Give Explaniation of each Proposal. 

Example format:

How will SEBI ensure that [specific reform] does not create duplicative compliance obligations for already listed entities?

What mechanisms are in place to align this reform with global capital-market standards?
(Continue up to 5.)
{circular_text}"""

def get_circular_prompt(circular_text):
    return f"""You are a regulatory document analyst specializing in financial and securities law. 
Carefully read the uploaded circular/regulatory document and provide a structured, 
detailed summary covering ALL of the following sections:

---

**1. DOCUMENT IDENTIFICATION**
- Circular/Reference Number
- Date of Issue
- Issuing Authority
- Addressed To (recipients)
- Signatory and Designation

---

**2. SUBJECT / PURPOSE**
- State the exact subject line
- Explain in plain language what this circular is about and why it was issued

---

**3. BACKGROUND & CONTEXT**
- What existing regulation, rule, or earlier circular is this building upon?
- What problem, gap, or representation triggered this circular?

---

**4. REFERENCES TO PREVIOUS CIRCULARS / REGULATIONS**
- List every prior circular, regulation, or legal provision mentioned
- For each, provide: Name, Number/Reference, Date (if mentioned), and its 
  relevance to the current circular

---

**5. KEY CHANGES / DIRECTIONS**
- What specific changes, modifications, or clarifications are being made?
- If any paragraph or provision is being replaced or amended, state both 
  the OLD text and the NEW text side by side
- Who is affected by these changes?

---

**6. NEW REQUIREMENTS & OBLIGATIONS**
- List all new obligations imposed on any party (e.g., timelines, 
  reporting duties, disclosures, compliances)
- Include specific deadlines, frequencies, or formats if mentioned

---

**7. LEGAL BASIS / AUTHORITY**
- Under which Act(s), Section(s), or Regulation(s) is this circular issued?

---

**8. EFFECTIVE DATE**
- When does this circular come into force?

---

**9. WHERE TO ACCESS**
- Mention any website or official source where this circular is published

---

**10. PLAIN LANGUAGE SUMMARY**
- Write a 5–8 line simple summary that a non-legal person can easily 
  understand — what changed, why it changed, and what action (if any) 
  is needed

---

Instructions:
- Do NOT skip any section. If information is not available for a section, 
  write "Not mentioned in the document."
- Preserve all proper nouns, reference numbers, dates, and regulation 
  names exactly as they appear in the document.
- Highlight any deadlines or action items in **bold**.
- If a provision has sub-clauses or conditions, list each one separately.

Document text:
{circular_text}"""
