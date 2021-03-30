from .serializers import PaperViewSet
from rest_framework.response import Response
import random

class GraphVisPaperViewSet(PaperViewSet):
    def list(self, request):
        # Get papers
        list_of_paper = self._get_list(request)
        
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