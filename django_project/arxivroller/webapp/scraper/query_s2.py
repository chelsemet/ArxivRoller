# Scraping From Semantic Scholar
from .utils import PaperNotFoundError
import requests
from .query import query_single_paper
import importlib.util
import time
import re
import os
from bs4 import BeautifulSoup
import dateutil
import dateutil.parser
import datetime
from django.conf import settings

# print(settings.SEMANTIC_SCHOLAR_KEY)
# print(settings.SEMANTIC_SCHOLAR_URL)

S2_KEY=settings.SEMANTIC_SCHOLAR_KEY
ROOT_URL=settings.SEMANTIC_SCHOLAR_URL+"/v1/paper/"
PAGE_ROOT_URL="https://api.semanticscholar.org/"

def query_page_s2(paper_id, try_get_pdf=True):
    if S2_KEY is None:
        response = requests.get(ROOT_URL + paper_id)
        time.sleep(0.1)
    else:
        response = requests.get(ROOT_URL + paper_id, headers={'x-api-key': S2_KEY})
        time.sleep(1.0/100)
    # print(ROOT_URL + paper_id)
    api_data = response.json()
    # print(api_data)
    # print(api_data.keys())
    # print(api_data['citationVelocity'])
    # print(api_data['topics'])
    # print(api_data['is_open_access'])
    # print(api_data['citations'])


    s2_info = {
        's2_id': api_data['paperId'],
        'arxiv_id': api_data['arxivId'] if api_data['arxivId'] is not None else f"s2:{api_data['paperId']}",
        'citation_velocity': api_data['citationVelocity'],
        'corpus_id': api_data['corpusId'],
        'doi': str(api_data['doi']),
        'fields_of_study': api_data['fieldsOfStudy'],
        'influential_citation_count': api_data['influentialCitationCount'],
        'is_open_access': api_data['isOpenAccess'],
        'is_publisher_licensed': api_data['isPublisherLicensed'],
        'topics': [t['topic'] for t in api_data['topics']],
        'url': str(api_data['url']),
        'venue': str(api_data['venue']),
        'year': api_data['year'],
        'updated': datetime.datetime.now(tz=dateutil.tz.tzutc()),
        'citations': [
            p['arxivId'] if p['arxivId'] is not None else f"s2:{p['paperId']}"
            for p in api_data['citations']
        ],
        'references': [
            p['arxivId'] if p['arxivId'] is not None else f"s2:{p['paperId']}"
            for p in api_data['references']
        ],
    }

    if 'error' in api_data:
        assert api_data['error'] == 'Paper not found'
        raise PaperNotFoundError()
    if api_data['arxivId'] is not None:
        return query_single_paper(api_data['arxivId']), s2_info
    d = {}
    d["arxiv_id"] = f"s2:{api_data['paperId']}"
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

    if try_get_pdf:
        if "pdf_url" not in d or d["pdf_url"] is None:
            page_response = requests.get(PAGE_ROOT_URL + paper_id)
            soup = BeautifulSoup(page_response.text, 'html.parser')
            # print(soup.title)

            if "[PDF]" in soup.title.string:
                for link in soup.find_all('a', {'class': 'alternate-source-link-button'}) + soup.find_all('a', {'class': 'button--primary'}):
                    if '.pdf' in link.get('href'):
                        d["pdf_url"] = link.get('href')
                        break 
            
        if "pdf_url" not in d or d["pdf_url"] is None:
            if d["doi"] is not None:
                # Try getting from scihub
                spec = importlib.util.spec_from_file_location("scihub", os.path.dirname(os.path.abspath(__file__))+"/scihub_pythonapi/scihub/scihub.py")
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

    return d, s2_info

def query_single_paper_s2(paper_id, try_get_pdf=True):
    """
    Download and parse a single paper from arxiv.
    """
    try:
        paper_info, s2_info = query_page_s2(paper_id=paper_id, try_get_pdf=try_get_pdf)
    except requests.HTTPError as e:
        print(e)
        # This seems to mean the ID was badly formatted
        if e.response.status_code == 400:
            raise PaperNotFoundError()
        raise
    if not paper_info:
        raise PaperNotFoundError()
    return paper_info, s2_info

# query_page_s2('47be321bff23f73c71d7e5716cd107ead087c3ae')