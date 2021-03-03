### Import data from https://www.kaggle.com/Cornell-University/arxiv
from ..models import Paper
from django.conf import settings
import json
import dateutil.parser
from tqdm import tqdm
from .scrape_arxiv import parse_cats

# Control the import categories
cats = parse_cats("ml eess stat cs".split(" "))

def convert_entry_to_paper(entry):
    """
    Convert an ElementTree <entry> into a dictionary to initialize a paper
    with.
    """
    d = {}
    d["arxiv_id"] = entry['id']
    d["title"] = entry['title']
    d["title"] = d["title"].replace("\n", "").replace("  ", " ")
    d["published"] = dateutil.parser.parse(entry['versions'][0]['created'])
    d["updated"] = dateutil.parser.parse(entry['versions'][-1]['created'])
    d["summary"] = entry['abstract']
    d["authors"] = []
    for author in entry["authors_parsed"]:
        d["authors"].append(
            " ".join(author).strip()
        )
    d["arxiv_url"] = f"https://arxiv.org/abs/{entry['id']}"
    d["pdf_url"] = f"https://arxiv.org/pdf/{entry['id']}"
    d["categories"] = [i.strip() for i in entry["categories"].split(' ')]
    d["primary_category"] = d["categories"][0]
    # Optional
    d["comment"] = getattr(d, "comments", None)
    d["doi"] = getattr(d, "doi", None)
    d["journal_ref"] = getattr(d, "journal-ref", None)

    # Remove version from everything
    d["arxiv_version"] = int(entry['versions'][-1]['version'].lower().replace('v',''))

    return d


def run(*args):
    if len(args) > 0:
        path = args[0]
    else:
        raise RuntimeError("Must provide path")

    latestDate = None
    with open(path, "r") as file:
        for line in tqdm(file):
            entry = json.loads(line.strip())
            # print(entry)
            entry = convert_entry_to_paper(entry)
            if all([e not in cats for e in entry["categories"]]):
                continue
            obj, created = Paper.objects.update_or_create_from_api(entry)
            if latestDate is None or latestDate < entry['updated']:
                latestDate = entry['updated']
                print(latestDate)
            # if created:
            #     print(obj)
            # print(paper)
            # break
