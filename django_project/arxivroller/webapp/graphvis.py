from .serializers import PaperViewSet
from .models import Paper, Author, Category, UserPreference, UserPaper, S2Info
from rest_framework.response import Response
import random
import nltk
from nltk.stem.wordnet import WordNetLemmatizer
import gensim
import math
from scipy.spatial import distance
from .rake import Rake

NUM_TOPICS=10

class GraphVisPaperViewSet(PaperViewSet):
    def list(self, request):
        # Get papers
        list_of_paper = self._get_list(request)
        # Get Reference & Citation
        for p in list_of_paper:
            obj,_,_,_ = S2Info.objects.update_from_arxiv_id(arxiv_id=p['arxiv_id'])
            p['references'] = obj.references
            p['citations'] = obj.citations
            p['topics'] = obj.topics
            p['fields_of_study'] = obj.fields_of_study

        # Topic Modeling
        all_lda_topics, topic_scores = lda(list_of_paper)
        for p,t in zip(list_of_paper,topic_scores):
            p['lda_topics'] = t

        # Rake Keywords
        keywords = Rake().get_keywords_of_topic_abstracts([(p['title']+' '+p['summary']).replace('\n', ' ')  for p in list_of_paper])
        for p,kw in zip(list_of_paper,keywords):
            p['rake_keywords'] = [s.replace('  ', ' ') for s in kw[1]]
            print(p['rake_keywords'])

        # define distance functions
        def refOverlap(p1, p2):
            return len(set(p1['references']) & set(p2['references']))
        def rakeKeywordOverlap(p1, p2):
            return len(set(p1['rake_keywords']) & set(p2['rake_keywords']))
        def citationPath(p1, p2):
            overlap_ref = refOverlap(p1,p2)
            if p2['arxiv_id'] in p1['references'] or p1['arxiv_id'] in p2['references']:
                return 1, overlap_ref
            if p2['arxiv_id'] in p1['references'] or p1['arxiv_id'] in p2['references']:
                return 0.5, overlap_ref
            return 0, overlap_ref
        def ldaScore(p1, p2):
            # t1 = [ (1- sum([s for i,s in p1['lda_topics']]))/(NUM_TOPICS- len(p1['lda_topics'])) ]*NUM_TOPICS
            # t2 = [ (1- sum([s for i,s in p2['lda_topics']]))/(NUM_TOPICS- len(p2['lda_topics'])) ]*NUM_TOPICS
            t1 = [0]*NUM_TOPICS
            t2 = [0]*NUM_TOPICS
            for i,s in p1['lda_topics']:
                t1[i] = s
            for i,s in p2['lda_topics']:
                t2[i] = s
            jsd = distance.jensenshannon(t1, t2, 2.0)
            return round(1-min(1,max(0,jsd)),4)

        # Get links
        paper_relevence = []
        for j in range(len(list_of_paper)):
            for i in range(j):
                rel = {
                    'source': list_of_paper[i]['id'],
                    'target': list_of_paper[j]['id'],
                }
                
                rel['citation_path_score'], rel['reference_overlap_score'] = citationPath(list_of_paper[i], list_of_paper[j])
                rel['lda_topic_score'] = ldaScore(list_of_paper[i], list_of_paper[j])
                rel['rake_keyword_overlap_score'] = rakeKeywordOverlap(list_of_paper[i], list_of_paper[j])

                paper_relevence.append(rel)
                # print(rel['reference_overlap_score'], rel['citation_path_score'])


        return_data = {
            "nodes": list_of_paper,
            "links": paper_relevence,
            "lda_topics": all_lda_topics,
        }

        return Response(return_data)

def lda(papers):
    def clean(string):
        string = gensim.parsing.preprocessing.remove_stopwords(string)
        string = nltk.word_tokenize(string)
        stopwords = set(nltk.corpus.stopwords.words('english'))
        cleaned_string = []
        for i in string:
            i = WordNetLemmatizer().lemmatize(i.lower())
            if len(i) <= 2:
                continue
            elif i in stopwords:
                continue
            else:
                cleaned_string.append(i)
        return list(set(cleaned_string))
        
    corpus = [p['title']+' '+p['summary'] for p in papers]
    corpus = [clean(p) for p in corpus]
    d = gensim.corpora.Dictionary(corpus)
    d.filter_extremes(no_below=2, no_above=0.4, keep_n=1000)
    corpus = [d.doc2bow(p) for p in corpus]

    ldamodel = gensim.models.ldamodel.LdaModel(corpus, num_topics=NUM_TOPICS, id2word=d, alpha='auto')
    topics = ldamodel.print_topics(num_words=10)
    all_topics = []
    for topic in topics:
        topic = topic[1].split("+")
        topic = [t.replace('"','').split('*') for t in topic]
        topic = [(float(t[0]), t[1].strip()) for t in topic]
        all_topics.append(topic)
        
    return all_topics, [ldamodel.get_document_topics(p) for p in corpus]



ALL_PATH_VIEWSET = {
    r'graphvis_papers': GraphVisPaperViewSet,
}
