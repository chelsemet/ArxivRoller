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

        # print(list_of_paper)
        # Get links

        paper_relevence = []
        for j in range(len(list_of_paper)):
            for i in range(j):
                paper_relevence.append(
                    {
                        'source': list_of_paper[i]['id'],
                        'target': list_of_paper[j]['id'],
                        'random_sim': random.random(),
                        'const_sim': 1,
                    })


        return_data = {
            "nodes": list_of_paper,
            "links": paper_relevence,
        }

        return Response(return_data)

ALL_PATH_VIEWSET = {
    r'graphvis_papers': GraphVisPaperViewSet,
}