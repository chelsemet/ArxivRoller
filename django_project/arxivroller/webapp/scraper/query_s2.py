# Scraping From Semantic Scholar
from .utils import PaperNotFoundError
import requests
from .query import query_single_paper
import importlib.util
import time
import re
import os
from bs4 import BeautifulSoup
import dateutil.parser

ROOT_URL="https://api.semanticscholar.org/v1/paper/"
PAGE_ROOT_URL="https://api.semanticscholar.org/"

def query_page_s2(paper_id):
    response = requests.get(ROOT_URL + paper_id)
    api_data = response.json()
    print(api_data.keys())
    if 'error' in api_data:
        assert api_data['error'] == 'Paper not found'
        raise PaperNotFoundError()
    if api_data['arxivId'] is not None:
        return query_single_paper(api_data['arxivId'])
    d = {}
    d["arxiv_id"] = f"s2:{paper_id}"
    d["title"] = api_data["title"]
    d["summary"] = api_data["abstract"]
    d["arxiv_url"] = api_data["url"]
    d["authors"] = [i['name'] for i in api_data['authors']]
    d["primary_category"] = "semantic-scholar"
    d["categories"] = ["semantic-scholar"]
    # Optional
    d["comment"] = "No Arxiv Paper Found"
    d["doi"] = api_data['doi']
    d["journal_ref"] = api_data['venue']
    d["arxiv_version"] = 0

    if "pdf_url" not in d or d["pdf_url"] is None:
        page_response = requests.get(PAGE_ROOT_URL + paper_id)
        soup = BeautifulSoup(page_response.text, 'html.parser')
        print(soup.title)

        if "[PDF]" in soup.title.string:
            for link in soup.find_all('a', {'class': 'alternate-source-link-button'}) + soup.find_all('a', {'class': 'button--primary'}):
                if '.pdf' in link.get('href'):
                    d["pdf_url"] = link.get('href')
                    break 
        
    if "pdf_url" not in d or d["pdf_url"] is None:
        if d["doi"] is not None:
            # Try getting from scihub
            spec = importlib.util.spec_from_file_location("scihub", os.path.dirname(os.path.abspath(__file__))+"./scihub_pythonapi/scihub/scihub.py")
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            scihub = mod.SciHub()
            for i in range(10):
                try: 
                    d["pdf_url"] = scihub.fetch(d["doi"])['url'].replace("#view=FitH","")
                    break
                except:
                    # time.sleep(2)
                    continue
    if "pdf_url" not in d or d["pdf_url"] is None:
        d["pdf_url"] = "https://scholar.google.com/scholar?q=" +d["title"]

    d["published"] = dateutil.parser.parse(str(api_data['year'])+'-1-1T00:00:00-00:00')
    d["updated"] = dateutil.parser.parse(str(api_data['year'])+'-1-1T00:00:00-00:00')
    # print(d)

    return d

    for author in entry.findall("atom:author", NS):
        d["authors"].append(
            author.find("atom:name", NS).text
        )
    d["pdf_url"] = entry.find("./atom:link[@type='application/pdf']", NS).attrib["href"]
    
    return response

def query_single_paper_s2(paper_id):
    """
    Download and parse a single paper from arxiv.
    """
    try:
        result = query_page_s2(paper_id=paper_id)
    except requests.HTTPError as e:
        print(e)
        # This seems to mean the ID was badly formatted
        if e.response.status_code == 400:
            raise PaperNotFoundError()
        raise
    if not result:
        raise PaperNotFoundError()
    return result