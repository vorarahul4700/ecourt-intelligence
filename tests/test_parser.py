import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from ecourt.parser import parse_case_html

SAMPLE_HTML = """
<h2 class='h4 text-center  mb-1' id='chHeading'>Jr. Civil Courts, Secunderabad - CCC</h2>
<h3 class='h2class fw-bold text-center'>Case Details</h3>
<table class="table case_details_table table-bordered">
    <tbody>
        <tr>
            <th class="fw-bold" id="fn6">Case Type</th>
            <td colspan='3' class="fw-bold text-uppercase" headers="fn6">OS - ORIGINAL SUIT</td>
        </tr>
        <tr>
            <th class="fw-bold" id="fn7">Filing Number</th>
            <td class="fw-bold" headers="fn7">44/2026</td>
            <th class="fw-bold" id="fn8">Filing Date</th>
            <td class="fw-bold" headers="fn8">29-01-2026</td>
        </tr>
        <tr>
            <th class="fw-bold" id="fn9">Registration Number</th>
            <td class="fw-bold" headers="fn9">35/2026</td>
            <th class="fw-bold" id="fn10">Registration Date</th>
            <td class="fw-bold" headers="fn10">29-01-2026</td>
        </tr>
        <tr>
            <th id='fn13'><b>CNR Number</b></th>
            <td colspan='2' headers='fn13'><span class="fw-bold text-uppercase fs-5 me-2 text-danger">TSHC070000392026</span></td>
            <td><a href='#'>View QR Code</a></td>
        </tr>
        <tr>
            <th class='fw-bold' id='fn14'>e-Filing Number</th>
            <td class='fw-bold text-uppercase' headers='fn14'>ATS20250012328C202600007</td>
            <th class='fw-bold' id='fn15'>e-Filing Date</th>
            <td class='fw-bold text-uppercase' headers='fn15'>29-01-2026</td>
        </tr>
    </tbody>
</table>

<h3 class="h2class fw-bold text-center mt-2 text-danger">Case Status</h3>
<table class="table case_status_table table-bordered">
    <tbody>
        <tr><th scope='row'>First Hearing Date</th><td>29th January 2026</td></tr>
        <tr><th scope='row'>Next Hearing Date</th><td><strong>25th November 2026</strong></td></tr>
        <tr><th scope='row'>Case Stage</th><td><strong>WRITTEN STATEMENT</strong></td></tr>
        <tr><th scope='row'>Court Number and Judge</th><td><strong> 1-I Junior Civil Judge</strong></td></tr>
    </tbody>
</table>

<h3 class='h2class fw-bold text-center mt-2 text-dark'>Petitioner and Advocate</h3>
<ul class='table table-bordered Petitioner_Advocate_table petitioner-advocate-list border'>
    <li>1) Gali Shiva Alias A Shiva<br />&nbsp;&nbsp;&nbsp;Advocate- G SRIKANTH<br /></li>
</ul>

<h3 class='h2class fw-bold text-center mt-2 text-dark'>Respondent and Advocate</h3>
<ul class='table table-bordered Respondent_Advocate_table respondent-advocate-list border'>
    <li>1) Rachana Jaiswal </li>
</ul>

<h3 class='h2class fw-bold text-center mt-2 text-dark'>Acts</h3>
<table class="table acts_table table-bordered" border="1" id='act_table'>
    <tr><th>Under Act(s)</th><th>Under Section(s)</th></tr>
    <tr><td>SPECIFIC RELIEF ACT</td><td>Section 38</td></tr>
</table>

<h3 class='h2class fw-bold text-center'>Processes</h3>
<table id='process' class='table table-fixed table-bordered table-responsive mt-2 FIR_details_table'>
    <thead><tr><th>Process ID</th><th>Process Title</th><th>Process Date</th></tr>
    <td>PTSHC070000392026_1_2</td><td>Summons to appear in person [O.5, R. 3]</td><td>02-02-2026</td>
    </thead>
</table>

<h3 class='h2class'>IA Status</h3>
<table class='IAheading table acts_table table-bordered' border='1'>
    <tr><th>IA Number</th><th>Party Name</th><th>Date of Filing</th><th>Next Date</th><th>IA Status</th></tr>
    <tr><td>IA/1/2026</td><td>Gali Shiva Alias A Shiva<br/>Rachana Jaiswal</td><td>29-01-2026</td><td>25-11-2026<br>(NOTICE)</td><td>Pending</td></tr>
</table>

<div id='historyheading'><h3 class='h2class'>Case History</h3></div>
<table class="history_table table" border="1">
    <thead><th>Judge</th><th>Business on Date</th><th>Hearing Date</th><th>Purpose of Hearing</th></thead>
    <tbody>
        <tr><td>I Junior Civil Judge</td><td>26-10-2026</td><td>25-11-2026</td><td>WRITTEN STATEMENT</td></tr>
    </tbody>
</table>
"""


def test_parse_case_html():
    data = parse_case_html(SAMPLE_HTML)
    assert data["court_name"] == "Jr. Civil Courts, Secunderabad - CCC"
    assert data["case_details"]["case_type"] == "OS - ORIGINAL SUIT"
    assert data["case_details"]["filing_number"] == "44/2026"
    assert data["case_details"]["cnr_number"] == "TSHC070000392026"
    assert data["case_status"]["next_hearing_date"] == "25th November 2026"
    assert len(data["petitioners"]) == 1
    assert data["petitioners"][0]["name"] == "Gali Shiva Alias A Shiva"
    assert data["petitioners"][0]["advocate"] == "G SRIKANTH"
    assert len(data["respondents"]) == 1
    assert data["respondents"][0]["name"] == "Rachana Jaiswal"
    assert len(data["acts"]) == 1
    assert data["acts"][0]["under_act"] == "SPECIFIC RELIEF ACT"
    assert len(data["processes"]) == 1
    assert data["processes"][0]["process_id"] == "PTSHC070000392026_1_2"
    assert len(data["ia_status"]) == 1
    assert data["ia_status"][0]["ia_number"] == "IA/1/2026"
    assert len(data["case_history"]) == 1
    assert data["case_history"][0]["business_on_date"] == "26-10-2026"


if __name__ == "__main__":
    test_parse_case_html()
    print("All parser unit tests passed successfully!")
