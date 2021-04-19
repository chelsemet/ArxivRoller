from .serializers import PaperViewSet
from .models import Paper, Author, Category, UserPreference, UserPaper, S2Info
from rest_framework.response import Response
import random

class GraphVisPaperViewSet(PaperViewSet):
    def list(self, request):
        # Get papers
        list_of_paper = self._get_list(request)
        # Get Reference & Citation
        for p in list_of_paper:
            obj,_,_,_ = S2Info.objects.update_from_arxiv_id(arxiv_id=p['arxiv_id'])
            p['references'] = obj.references
            p['citations'] = obj.citations

        # defein distance functions
        def refOverlap(p1, p2):
            return len(set(p1['references']) & set(p2['references']))
        def citationPath(p1, p2):
            overlap_ref = refOverlap(p1,p2)
            if p2['arxiv_id'] in p1['references'] or p1['arxiv_id'] in p2['references']:
                return 1, overlap_ref
            if p2['arxiv_id'] in p1['references'] or p1['arxiv_id'] in p2['references']:
                return 0.5, overlap_ref
            return 0, overlap_ref

        # Get links
        paper_relevence = []
        for j in range(len(list_of_paper)):
            for i in range(j):
                rel = {
                    'source': list_of_paper[i]['id'],
                    'target': list_of_paper[j]['id'],
                }
                
                rel['citation_path_score'], rel['reference_overlap_score'] = citationPath(list_of_paper[i], list_of_paper[j])

                paper_relevence.append(rel)
                # print(rel['reference_overlap_score'], rel['citation_path_score'])


        return_data = {
            "nodes": list_of_paper,
            "links": paper_relevence,
        }

        return Response(return_data)

ALL_PATH_VIEWSET = {
    r'graphvis_papers': GraphVisPaperViewSet,
}