from .models import Paper, Author, Category, UserPreference, UserPaper, S2Info
from rest_framework import serializers, viewsets, status, permissions
from rest_framework.authentication import SessionAuthentication, BasicAuthentication
from rest_framework.permissions import IsAuthenticated, BasePermission
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.decorators import api_view
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.db import transaction, models
from django.db.models import Q, F, Func, Value
from django.conf import settings
from django.contrib.postgres.fields import ArrayField
from django.contrib.postgres.search import SearchQuery, SearchVector, SearchRank

import time
import json
import collections
    
if settings.DEBUG:
    logger = print 
else:
    logger = lambda *args, **kwargs: None


class IsAdminUserOrReadOnly(BasePermission):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return bool(request.user and request.user.is_authenticated)
        else:
            # Check permissions for write request
            return bool(request.user and request.user.is_staff)

# api for user-paper
# Serializers define the API representation.
class UserPaperSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserPaper
        fields = UserPaper.get_api_fields()

# api for paper 
# Serializers define the API representation.
class PaperSerializer(serializers.ModelSerializer):
    class Meta:
        model = Paper
        fields = Paper.get_api_fields()

# ViewSets define the view behavior.
class PaperViewSet(viewsets.ModelViewSet):
    # permission_classes = (permissions.IsAuthenticatedOrReadOnly,)
    permission_classes = [IsAdminUserOrReadOnly]
    queryset = Paper.objects.all()
    serializer_class = PaperSerializer

    def _get_list(self, request):
        start_time = time.time()
        user = request.user

        queryset = Paper.objects.all()

        search_arxiv_id = request.query_params.get('arxiv_id', None)
        search_s2_id = request.query_params.get('s2_id', None)
        search_unknown_id = request.query_params.get('unknown_id', None)
        if search_arxiv_id is not None:
            queryset = queryset.filter(arxiv_id=search_arxiv_id)
        elif search_s2_id is not None:
            obj,_ = Paper.objects.update_from_s2_id(paper_id=search_s2_id)
            queryset = queryset.filter(arxiv_id=obj.arxiv_id)
            # return Response("Not implemented Error", status=status.HTTP_400_BAD_REQUEST)
        elif search_unknown_id is not None:
            return Response("Not implemented Error", status=status.HTTP_400_BAD_REQUEST)

        # Full Text Search
        def fullTextSearch(queryset, search_vector, search_query):
            # search_query = SearchQuery(search_query, search_type='raw')
            search_query = SearchQuery(search_query, search_type='websearch')
            queryset = queryset.filter(**{"_".join(search_vector) + "_search_vector": search_query})
            return queryset
            
        search_title = request.query_params.get('title', "")
        search_summary = request.query_params.get('summary', "")
        search_bothtext = request.query_params.get('bothtext', "")

        search_engine = request.query_params.get('searchEngine', 'fts')
        
        if search_engine.lower().strip() in ['fts','full-text', 'full-text-search']:
            if search_bothtext != "":
                queryset = fullTextSearch(queryset, ['title', 'summary'], search_bothtext)
            elif search_title != "":
                queryset = fullTextSearch(queryset, ['title'], search_title)
            elif search_summary != "":
                queryset = fullTextSearch(queryset, ['summary'], search_summary)
        elif search_engine.lower().strip() == 'simple':
            search_bothtext = search_bothtext.lower()
            if search_bothtext != "":
                queryset = queryset.filter(Q(title__icontains=search_bothtext) | Q(summary__icontains=search_bothtext))
            elif search_title != "":
                queryset = queryset.filter(Q(title__icontains=search_bothtext))
            elif search_summary != "":
                queryset = queryset.filter(Q(summary__icontains=search_bothtext))
        

        search_author = request.query_params.get('author', None)
        if search_author is not None:
            search_author=search_author.split(",")
            for au in search_author:
                queryset = queryset.filter(authors_m2m=au).distinct()
        
        search_overlap_author = request.query_params.get('overlapAuthor', None)
        if search_overlap_author is not None:
            search_overlap_author=search_overlap_author.split(",")
            queryset = queryset.filter(authors_m2m__in=search_overlap_author).distinct()
        
        search_cats = request.query_params.get('cats', None)
        # logger("===="+search_cats+"====")
        if search_cats is not None:
            search_cats=search_cats.split(" ")
            for cat in search_cats:
                queryset = queryset.filter(categories_m2m=cat).distinct()
            
        search_overlap_cats = request.query_params.get('overlapCats', None)
        if search_overlap_cats is not None:
            search_overlap_cats=search_overlap_cats.split(" ")
            if "all" not in search_overlap_cats:
                queryset = queryset.filter(categories__overlap=search_overlap_cats)
        
        # queryset = queryset.distinct()

        # logger("Before user filter", time.time()-start_time)
        # start_time = time.time()
        # Filter by user paper
        def boolUserPaperFilter(param, queryset, default_state = False):
            """
            default_state is the default state for handling non-exist userpaper objs
            """
            search_param = request.query_params.get(param, None)
            if search_param is None or search_param.lower() not in ["true", "false"]:
                return queryset
            search_param = True if search_param.lower() == "true" else False
            user_paper = UserPaper.objects.filter(user = user)
            user_paper = user_paper.filter(**{param: not default_state})
            user_paper_ids = [i[0] for i in user_paper.values_list('paper__id').distinct()]
            # logger(user_paper_ids)
            if search_param == default_state:
                queryset = queryset.exclude(id__in=user_paper_ids)
            else:
                queryset = queryset.filter(id__in=user_paper_ids)
            return queryset
        for param in ['read_status','archive_status', 'star_status']:
            queryset = boolUserPaperFilter(param, queryset)

        search_tags = request.query_params.get("tags", None)
        if search_tags is not None:
            search_tags=search_tags.split(",")
            user_paper = UserPaper.objects.filter(user = user)
            user_paper = user_paper.filter(tags__contains=search_tags)
            user_paper_ids = [i[0] for i in user_paper.values_list('paper__id').distinct()]
            queryset = queryset.filter(id__in=user_paper_ids)
            
        search_tags = request.query_params.get("overlapTags", None)
        if search_tags is not None:
            search_tags=search_tags.split(",")
            user_paper = UserPaper.objects.filter(user = user)
            user_paper = user_paper.filter(tags__overlap=search_tags)
            user_paper_ids = [i[0] for i in user_paper.values_list('paper__id').distinct()]
            queryset = queryset.filter(id__in=user_paper_ids)
        
        # logger("After user filter", time.time()-start_time)
        # start_time = time.time()

        # queryset = queryset.distinct()
        order_by = request.query_params.get('orderBy', None)
        if order_by is None or order_by == "latest":
            queryset = queryset.order_by("updated").reverse()
        else:
            order_by = order_by.split(" ")
            queryset = queryset.order_by(order_by[0])
            if order_by[1]=="reverse":
                queryset = queryset.reverse()

        max_returns = int(request.query_params.get('max_returns', 20))
        start_id = int(request.query_params.get('start_id', 0))
        # logger(queryset.query)
        queryset = queryset[start_id:start_id+max_returns]

        serializer = PaperSerializer(queryset, many=True)
        return_data = serializer.data

        # Append User Status
        with transaction.atomic():
            assert len(queryset) == len(return_data)
            for paper, return_dict in zip(queryset,return_data):
                user_paper, created = UserPaper.objects.get_or_create(user=user, paper=paper)
                user_paper_details = UserPaperSerializer(user_paper).data
                return_dict['user_paper'] = user_paper_details
        # logger(return_data[0])

        print(f"Query Cost: {time.time()-start_time:.4f}")
        # start_time = time.time()
        return return_data
    
    def list(self, request):
        return Response(self._get_list(request))

# api for user preference
class PreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserPreference
        fields = ['prefer_categories']


@api_view(['GET', 'POST'])
def user_tags(request, format=None):
    """
    Get all tags of a user
    """
    start_time = time.time()
    user = request.user
    tags = UserPaper.objects.filter(user = user).annotate(tags_els=Func(F('tags'), function='unnest'))\
                .values_list('tags_els', flat=True).distinct()
    # print(tags)
    tags = list(tags)
    q = request.query_params.get('q', None)
    if q is not None:
        tags = [t for t in tags if q.lower() in t.lower()]
    # tags = json.dumps(tags)
    print(f"Query Cost: {time.time()-start_time:.4f}")
    
    # logger(tags.query)
    # logger(tags)
    assert request.method == 'GET'
    return Response(tags)

@api_view(['POST'])
def rename_tag(request, format=None):
    """
    Get all tags of a user
    """
    oldtag = request.query_params['oldtag']
    newtag = request.query_params['newtag']
    user = request.user
    logger(f"Rename Tag: {oldtag} -> {newtag}")

    papers = UserPaper.objects.filter(user = user)
    papers.update(tags = Func(F('tags'), Value(oldtag), Value(newtag), output_field=ArrayField(models.CharField(max_length=100), default=list, blank=True), function='ARRAY_REPLACE'))

    assert request.method == 'POST'
    return Response({})

@api_view(['GET', 'POST'])
def user_profile(request, format=None):
    """
    Get all statistics for a user
    """
    start_time = time.time()
    user = request.user

    papers = UserPaper.objects.filter(user = user)

    tags = papers.annotate(tags_els=Func(F('tags'), function='unnest'))\
                .values_list('tags_els', flat=True)
    tags = collections.Counter(list(tags))

    read_papers = sum(papers.values_list('read_status', flat=True))
    star_papers = sum(papers.values_list('star_status', flat=True))
    archive_papers = sum(papers.values_list('archive_status', flat=True))


    print(f"Query Cost: {time.time()-start_time:.4f}")
    
    # logger(tags.query)
    # logger(tags)
    assert request.method == 'GET'
    return Response({
        'tags': tags,
        'read_papers': read_papers,
        'star_papers': star_papers,
        'archive_papers': archive_papers,
    })


@api_view(['GET', 'POST'])
def user_preference(request, format=None):
    """
    Get user preference
    """
    user = request.user
    if hasattr(user, 'userpreference'):
        preference = user.userpreference
    else:
        preference = UserPreference(user=user)
        preference.save()

    if request.method == 'GET':
        serializer = PreferenceSerializer(preference)
        return Response(serializer.data)

    elif request.method == 'POST':
        newdata = {}
        for k,v in request.data.items():
            if k == 'prefer_categories':
                newdata['prefer_categories'] = [cat.strip() for cat in v.split(',')]
            else:
                newdata[k] = v

        serializer = PreferenceSerializer(preference, data=newdata, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET', 'POST'])
def user_paper(request, format=None):
    """
    Get status for a given paper
    """
    user = request.user
    paper_id = request.query_params.get('paper_id', None)
    if paper_id is None:
        return Response("paper_id is not given", status=status.HTTP_400_BAD_REQUEST)
    paper = Paper.objects.get(id=paper_id)
    user_paper, _ = UserPaper.objects.get_or_create(user=user, paper=paper)

    if request.method == 'GET':
        user_paper_details = UserPaperSerializer(user_paper).data
        return Response(user_paper_details)
    elif request.method == 'POST':
        # logger(request.data.keys())
        # logger(request.data)
        update_dict = {}
        for k,v in request.data.items():
            if k == "tags":
                # Speicial Love
                v = json.loads(v)
            update_dict[k] = v
        # logger(user_paper.id)
        # logger(update_dict)
        serializer = UserPaperSerializer(user_paper, data=update_dict, partial=True)
        
        if serializer.is_valid(raise_exception=True):
            serializer.save()
            # logger(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

ALL_PATH_VIEWSET = {
    r'papers': PaperViewSet,
}