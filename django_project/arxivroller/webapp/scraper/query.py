from .utils import query_page, PaperNotFoundError
import requests


def query_multi_papers(paper_ids, max_results=100, session=None):
    """
    Download and parse a multiple papers from arxiv.
    """
    try:
        result = list(query_page(id_list=paper_ids, max_results=max_results, session=session))
    except requests.HTTPError as e:
        print(e)
        # This seems to mean the ID was badly formatted
        if e.response.status_code == 400:
            raise PaperNotFoundError()
        raise
    if not result:
        raise PaperNotFoundError()
    return result

def query_single_paper(paper_id):
    """
    Download and parse a single paper from arxiv.
    """
    result = query_multi_papers(paper_ids=[paper_id], max_results=1)
    return result[0]

def query_papers_by_subject(subject, start=0, max_results=100, session=None, sortOrder="descending"):
    subject = subject.strip().split(' ')
    search_query=" OR ".join(f"cat:{s}" for s in subject)
    try:
        result = list(query_page(search_query=search_query, start=start, max_results=max_results, session=session, sortOrder=sortOrder))
    except requests.HTTPError as e:
        print(e)
        # This seems to mean the ID was badly formatted
        if e.response.status_code == 400:
            raise PaperNotFoundError()
        raise
    if not result:
        raise PaperNotFoundError()
    return result