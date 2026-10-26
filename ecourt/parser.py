import re
from bs4 import BeautifulSoup
from typing import Dict, Any, List, Optional


def clean_text(text: Optional[str]) -> str:
    """Helper to clean whitespace, &nbsp;, and extraneous chars."""
    if not text:
        return ""
    text = text.replace('\xa0', ' ').replace('&nbsp;', ' ')
    # Clean leading/trailing slashes or HTML artifact brackets
    text = re.sub(r'^[/>\s]+', '', text)
    text = re.sub(r'[/>\s]+$', '', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def parse_case_html(html_content: str) -> Dict[str, Any]:
    """
    Robust parser for eCourts casetype_list HTML, accounting for idiosyncratic
    government portal markup (unclosed tags, <td> directly inside thead, missing tr).
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    data: Dict[str, Any] = {
        "court_name": "",
        "case_details": {},
        "case_status": {},
        "petitioners": [],
        "respondents": [],
        "acts": [],
        "processes": [],
        "ia_status": [],
        "case_history": []
    }

    # 1. Court Name
    heading_el = soup.find(id='chHeading') or soup.find('h2')
    if heading_el:
        data["court_name"] = clean_text(heading_el.text)

    # 2. Case Details Table
    details_table = soup.find('table', class_='case_details_table')
    if details_table:
        for row in details_table.find_all('tr'):
            th_cells = row.find_all('th')
            td_cells = row.find_all('td')
            
            i_th = 0
            i_td = 0
            while i_th < len(th_cells) and i_td < len(td_cells):
                key = clean_text(th_cells[i_th].text)
                val_cell = td_cells[i_td]
                if "CNR Number" in key:
                    cno_span = val_cell.find('span')
                    val = clean_text(cno_span.text) if cno_span else clean_text(val_cell.text)
                else:
                    val = clean_text(val_cell.text)
                
                key_norm = key.lower().replace(' ', '_').replace('-', '_')
                data["case_details"][key_norm] = val
                i_th += 1
                i_td += 1

    # 3. Case Status Table
    status_table = soup.find('table', class_='case_status_table')
    if status_table:
        for row in status_table.find_all('tr'):
            th = row.find('th')
            td = row.find('td')
            if th and td:
                key = clean_text(th.text).lower().replace(' ', '_')
                val = clean_text(td.text)
                data["case_status"][key] = val

    # 4. Petitioner & Advocate
    pet_ul = soup.find('ul', class_='Petitioner_Advocate_table')
    if pet_ul:
        for li in pet_ul.find_all('li'):
            # Use get_text with newline separator
            lines = [clean_text(l) for l in li.get_text(separator="\n").splitlines() if clean_text(l)]
            name = ""
            advocate = ""
            for line in lines:
                if re.match(r'^\d+\)', line):
                    name = re.sub(r'^\d+\)\s*', '', line).strip()
                elif 'advocate' in line.lower():
                    advocate = re.sub(r'^advocate[\s:\-]*', '', line, flags=re.IGNORECASE).strip()
                elif not name:
                    name = line
            
            if name or advocate:
                data["petitioners"].append({
                    "name": name,
                    "advocate": advocate or None
                })

    # 5. Respondent & Advocate
    resp_ul = soup.find('ul', class_='Respondent_Advocate_table')
    if resp_ul:
        for li in resp_ul.find_all('li'):
            lines = [clean_text(l) for l in li.get_text(separator="\n").splitlines() if clean_text(l)]
            name = ""
            advocate = ""
            for line in lines:
                if re.match(r'^\d+\)', line):
                    name = re.sub(r'^\d+\)\s*', '', line).strip()
                elif 'advocate' in line.lower():
                    advocate = re.sub(r'^advocate[\s:\-]*', '', line, flags=re.IGNORECASE).strip()
                elif not name:
                    name = line
            
            if name or advocate:
                data["respondents"].append({
                    "name": name,
                    "advocate": advocate or None
                })

    # 6. Acts Table
    act_table = soup.find('table', id='act_table') or soup.find('table', class_='acts_table')
    if act_table:
        for r in act_table.find_all('tr'):
            tds = r.find_all('td')
            if len(tds) >= 2:
                data["acts"].append({
                    "under_act": clean_text(tds[0].text),
                    "under_section": clean_text(tds[1].text)
                })

    # 7. Processes Table
    proc_table = soup.find('table', id='process') or soup.find('table', class_='FIR_details_table')
    if proc_table:
        # eCourts process tables frequently have loose <td> elements due to malformed markup
        # Let's extract all <td> elements and group them in chunks of 3
        all_tds = [clean_text(td.text) for td in proc_table.find_all('td')]
        # Group by 3: [id, title, date]
        for i in range(0, len(all_tds), 3):
            chunk = all_tds[i:i+3]
            if len(chunk) == 3 and chunk[0]:
                data["processes"].append({
                    "process_id": chunk[0],
                    "process_title": chunk[1],
                    "process_date": chunk[2]
                })

    # 8. IA Status Table
    ia_table = soup.find('table', class_='IAheading')
    if ia_table:
        for r in ia_table.find_all('tr'):
            tds = r.find_all('td')
            if len(tds) >= 5:
                # Next Date might contain "(Purpose)"
                raw_lines = [clean_text(l) for l in tds[3].get_text(separator="\n").splitlines() if clean_text(l)]
                next_date = raw_lines[0] if raw_lines else clean_text(tds[3].text)
                purpose = raw_lines[1] if len(raw_lines) > 1 else ""
                purpose = re.sub(r'^[(\s]+|[)\s]+$', '', purpose)

                # Party name
                party_lines = [clean_text(l) for l in tds[1].get_text(separator="\n").splitlines() if clean_text(l)]

                data["ia_status"].append({
                    "ia_number": clean_text(tds[0].text),
                    "party_name": " / ".join(party_lines) if party_lines else clean_text(tds[1].text),
                    "filing_date": clean_text(tds[2].text),
                    "next_date": next_date,
                    "purpose": purpose,
                    "status": clean_text(tds[4].text)
                })

    # 9. Case History Table
    hist_table = soup.find('table', class_='history_table')
    if hist_table:
        for r in hist_table.find_all('tr'):
            tds = r.find_all('td')
            if len(tds) >= 4:
                data["case_history"].append({
                    "judge": clean_text(tds[0].text),
                    "business_on_date": clean_text(tds[1].text),
                    "hearing_date": clean_text(tds[2].text),
                    "purpose_of_hearing": clean_text(tds[3].text)
                })

    return data
