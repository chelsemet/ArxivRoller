from ..models import Paper
from django.conf import settings
import time
import requests
import dateutil.parser
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode
from xml.etree import ElementTree

# MAX_PAPER=50000
# SCRAPE_ORDERS=['descending','ascending']
# SCRAPE_DATE = None

MAX_PAPER=1000
SCRAPE_ORDERS=['descending']
SCRAPE_DATE=datetime.now(timezone.utc) - timedelta(days=7) 
print(SCRAPE_DATE)

def parse_cats(cats):
    cats = set(cats)
    # Download all Papers
    if 'all' in cats:
        cats.remove('all')
        cats = cats.union(settings.ALL_CATEGORIES)
    # Download all Papers
    if 'ml' in cats:
        cats.remove('ml')
        cats = cats.union(settings.PAPERS_MACHINE_LEARNING_CATEGORIES)
    # Replace the main category by all sub categories
    for main_cat in ['cs', 'math', 'eess', 'cond-mat', 'q-bio', 'q-fin', 'stat', 'physics', 'nlin', 'astro-ph']:
        if main_cat in cats:
            cats.remove(main_cat)
            cats = cats.union([i for i in settings.ALL_CATEGORIES if i.startswith(main_cat)])
    return cats

def run(*args):
    session = requests.Session()

    if len(args) > 0:
        cats = parse_cats(args)
    else:
        cats = set(settings.PAPERS_MACHINE_LEARNING_CATEGORIES)
    
    cats = list(cats)
    cats.sort()
    for sub_i, subject_str in enumerate(cats):
        print(f"Scraping [{sub_i}/{len(cats)}]"+subject_str)
        # continue

        def get_maxresults():
            url_args = {"start": 0, "max_results": 10, "sortBy": "lastUpdatedDate"}
            url_args["search_query"] = f"cat:{subject_str}"
            response = session.get("http://export.arxiv.org/api/query?" + urlencode(url_args))
            root = ElementTree.fromstring(response.text)
            # print(root.tag)
            # for child in root:
            #     print(child.tag, child.attrib)
            entry = root.find(r"{http://a9.com/-/spec/opensearch/1.1/}totalResults")

            max_papers = int(entry.text)
            time.sleep(5)
            print(f"{subject_str} Total Ppaers: {max_papers}")
            return max_papers

        max_papers = get_maxresults()
        assert max_papers <= 50000*2, f"Exceeds maximum number {max_papers}"

        chunk_size = 200
        waiting = 5.0
        fail_num = 0
        for order in SCRAPE_ORDERS:
            for i in range(100000):
                while(True):
                    # results = Paper.objects.bulk_update_or_create_from_subject(subject=subject_str, 
                    #     start=chunk_size*i, 
                    #     max_results=chunk_size, 
                    #     session=session,
                    #     sortOrder=order)
                    # time.sleep(waiting)
                    try:
                        results = Paper.objects.bulk_update_or_create_from_subject(subject=subject_str, 
                            start=chunk_size*i, 
                            max_results=chunk_size, 
                            session=session,
                            sortOrder=order)
                        time.sleep(waiting)
                        break
                    except Exception as e:
                        fail_num+=1
                        waiting = 10.
                        print(f"Fail {fail_num} times. Wait {waiting} seconds.")
                        time.sleep(waiting)
                waiting = 5.0
                fail_num = 0 
                print(f"{(i+1):7d}*{chunk_size}: Arxiv:{results[-1][0].arxiv_id}, Date:{results[-1][0].updated}, created: {results[-1][1]}")
                if (i+1)*chunk_size >= max_papers \
                    or (i+1)*chunk_size >= MAX_PAPER \
                    or (order == "descending" and SCRAPE_DATE is not None and results[-1][0].updated < SCRAPE_DATE):
                    max_papers = min(max_papers-(i+1)*chunk_size + 1000, max_papers)
                    break
        
        