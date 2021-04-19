from django.db import models, transaction
from django.db.models import Value
from django.db.models.utils import resolve_callables 
from django.contrib.postgres.fields import ArrayField
from django.conf import settings
from django.urls import reverse
from datetime import timedelta
from django.contrib.auth.models import User
from django.contrib.postgres.search import SearchVectorField, SearchVector
from django.contrib.postgres.indexes import GinIndex

import time
import datetime
import dateutil
import dateutil.parser

from .scraper.query import query_single_paper, query_multi_papers, query_papers_by_subject
from .scraper.query_s2 import query_single_paper_s2


class PaperQuerySet(models.QuerySet):

    def updatenew_or_create(self, defaults=None, **kwargs):
        """
        Look up an object with the given kwargs, updating one with defaults
        if it exists, otherwise create a new one.
        Return a tuple (object, created), where created is a boolean
        specifying whether an object was created.
        """
        defaults = defaults or {}
        self._for_write = True
        with transaction.atomic(using=self.db):
            # Lock the row so that a concurrent update is blocked until
            # update_or_create() has performed its save.
            obj, created = self.select_for_update().get_or_create(defaults, **kwargs)
            if created:
                obj.update_m2m_fields(defaults=defaults, using=self.db, save=False)
                obj.update_search_vector(using=self.db, save=True)
                return obj, created
            # import ipdb; ipdb.set_trace()
            if "updated" in defaults:
                if defaults["updated"] < obj.updated:
                    return obj, False
            for k, v in resolve_callables(defaults):
                setattr(obj, k, v)
            obj.update_m2m_fields(defaults=defaults, using=self.db, save=False)
            obj.update_search_vector(using=self.db, save=False)
            obj.save(using=self.db)
        return obj, False

    def bulk_update_or_create_from_api(self, result):
        return [self.update_or_create_from_api(r) for r in result]

    def bulk_update_or_create_from_arxiv_id(self, arxiv_id, session=None):
        """
        Query the arXiv API and create multiple Papers from it by id list.
        Raises:
            `arxiv_vanity.scraper.query.PaperNotFoundError`: If paper does not exist on arxiv.
        """
        return self.bulk_update_or_create_from_api(query_multi_papers(arxiv_id, session=session))

    def bulk_update_or_create_from_subject(self, subject, start=0, max_results=100, session=None, sortOrder="descending"):
        """
        Query the arXiv API and create multiple Papers from it by id subject.
        Raises:
            `arxiv_vanity.scraper.query.PaperNotFoundError`: If paper does not exist on arxiv.
        """
        return self.bulk_update_or_create_from_api(
            query_papers_by_subject(subject=subject, start=start, max_results=max_results, session=session, sortOrder=sortOrder))

    def update_or_create_from_api(self, result):
        obj, created = self.updatenew_or_create(arxiv_id=result["arxiv_id"], defaults=result)
        # if created:
        #     obj.user.set(User.objects.all())
        return obj, created

    def update_or_create_from_arxiv_id(self, arxiv_id):
        """
        Query the arXiv API and create a Paper from it.
        Raises:
            `arxiv_vanity.scraper.query.PaperNotFoundError`: If paper does not exist on arxiv.
        """
        return self.update_or_create_from_api(query_single_paper(arxiv_id))
        
    def update_from_s2_id(self, paper_id):
        """
        Query the Semantic Scholar API and create a Paper from it.
        Raises:
            `arxiv_vanity.scraper.query.PaperNotFoundError`: If paper does not exist on arxiv.
        """
        _, _, obj, created = S2Info.objects.update_from_s2_id(paper_id)
        return obj, created

    def machine_learning(self):
        """
        Return only machine learning papers.
        """
        return self.filter(
            categories__overlap=settings.PAPERS_MACHINE_LEARNING_CATEGORIES
        )

class PaperManager(models.Manager):
    pass

class Author(models.Model):
    name = models.CharField(max_length=70, primary_key=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

class Category(models.Model):
    name = models.CharField(max_length=100, primary_key=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

class Paper(models.Model):
    """
    Main model for paper
    """
    # ArXiV fields
    arxiv_id = models.CharField(max_length=100, unique=True, db_index=True)
    arxiv_version = models.IntegerField()
    title = models.TextField()
    published = models.DateTimeField()
    updated = models.DateTimeField(db_index=True)
    summary = models.TextField()
    authors = ArrayField(models.CharField(max_length=70))
    authors_m2m = models.ManyToManyField(Author)
    arxiv_url = models.URLField()
    pdf_url = models.URLField()
    primary_category = models.CharField(max_length=100)
    categories = ArrayField(models.CharField(max_length=100))
    categories_m2m = models.ManyToManyField(Category)
    comment = models.TextField(null=True, blank=True)
    doi = models.CharField(null=True, blank=True, max_length=255)
    journal_ref = models.TextField(null=True, blank=True, max_length=255)

    # user relation
    user = models.ManyToManyField(settings.AUTH_USER_MODEL, through='UserPaper')

    # Full Text Search
    title_search_vector = SearchVectorField(null=True, editable=False)
    summary_search_vector = SearchVectorField(null=True, editable=False)
    title_summary_search_vector = SearchVectorField(null=True, editable=False)

    # define manager
    objects = PaperManager.from_queryset(PaperQuerySet)() 

    class Meta:
        get_latest_by = "updated"
        ordering = ['updated']
        indexes = [ 
            GinIndex(fields=['title_summary_search_vector']),
            GinIndex(fields=['title_search_vector']),
            GinIndex(fields=['summary_search_vector']),
         ]

    @classmethod
    def get_api_fields(cls):
        all_fileds = [f.name for f in cls._meta.fields]
        return all_fileds

    @classmethod
    def bulk_update_search_vector(cls):
        cls.objects.update(title_search_vector=SearchVector('title'))
        cls.objects.update(summary_search_vector=SearchVector('summary'))
        cls.objects.update(title_summary_search_vector=SearchVector('title', 'summary'))
        
    def update_search_vector(self, using=None, save=True):
        self.title_search_vector = SearchVector(Value(self.title, output_field=models.TextField()))
        self.summary_search_vector = SearchVector(Value(self.summary, output_field=models.TextField()))
        self.title_summary_search_vector = SearchVector(Value(self.title, output_field=models.TextField())) + \
                                        SearchVector(Value(self.summary, output_field=models.TextField()))
        # import ipdb; ipdb.set_trace()
        if save:
            self.save(using=using)
        return True

    def __str__(self):
        return self.title

    def get_date(self):
        return self.updated 

    def get_absolute_url(self):
        return reverse("paper_detail", args=(self.arxiv_id,))

    def get_https_arxiv_url(self):
        url = str(self.arxiv_url)
        if url.startswith("http://arxiv.org"):
            url = url.replace("http://", "https://")
        return url

    def get_https_pdf_url(self):
        url = str(self.pdf_url)
        if url.startswith("http://arxiv.org"):
            url = url.replace("http://", "https://")
        return url

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # self.update_m2m_fields(save=False)
        # self.update_search_vector(save=False)
        # super().save(*args, **kwargs)

    def update_m2m_fields(self, defaults=None, using=None, save=True):
        """
        Update many2many fields
        """
        updated = False
        if defaults is None:
            defaults = {
                "authors": self.authors,
                "categories": self.categories,
            }
        if "authors" in defaults:
            self.authors_m2m.clear()
            for name in set(defaults["authors"]):
                author, created = Author.objects.get_or_create(name=name)
                self.authors_m2m.add(author)
            updated = True
        if "categories" in defaults:
            self.categories_m2m.clear()
            for name in set(defaults["categories"]):
                cat, created = Category.objects.get_or_create(name=name)
                self.categories_m2m.add(cat)
            updated = True
        if updated and save:
            self.save(using=using)
        return updated

# Semantic Scholar Info
class S2InfoQuerySet(models.QuerySet):
    
    def update_from_arxiv_id(self, arxiv_id, try_get_pdf=False):
        if arxiv_id.startswith("s2:"):
            return self.update_from_s2_id(arxiv_id[3:], try_get_pdf=try_get_pdf)

        try:
            paper_obj = Paper.objects.get(arxiv_id=arxiv_id)
            if hasattr(paper_obj, 's2info'):
                return self.update_from_s2_id(paper_obj.s2info.s2_id, try_get_pdf=try_get_pdf)
            else:
                return self.update_from_s2_id('arXiv:'+arxiv_id, try_get_pdf=try_get_pdf)
        except Paper.objects.model.DoesNotExist:
            raise NotImplementedError()

        raise NotImplementedError()

    def update_from_s2_id(self, paper_id, try_get_pdf=False):
        """
        Query the Semantic Scholar API and create a Paper from it.
        Raises:
            `arxiv_vanity.scraper.query.PaperNotFoundError`: If paper does not exist on arxiv.
        """
        
        self._for_write = True
        with transaction.atomic(using=self.db):
            # Lock the row so that a concurrent update is blocked until
            # update_or_create() has performed its save.

            select_for_update = self.select_for_update()
            try:
                obj = select_for_update.get(s2_id=paper_id)
            except select_for_update.model.DoesNotExist:
                obj = None
            created = (obj is None)
            if created or (obj.updated-datetime.datetime.now(tz=dateutil.tz.tzutc())) > datetime.timedelta(days=30):
                paper_info, s2_info = query_single_paper_s2(paper_id, try_get_pdf=try_get_pdf)
                paper_obj, paper_created = Paper.objects.update_or_create_from_api(paper_info)
                
                with transaction.atomic(using=select_for_update.db):
                    obj = select_for_update.create(paper=paper_obj, **s2_info)
            else:
                paper_obj, paper_created = obj.paper, False
        return obj, created, paper_obj, paper_created


class S2InfoManager(models.Manager):
    pass
class S2Info(models.Model):
    """
    Main model for paper
    """
    # S2 fields
    s2_id = models.CharField(max_length=100, unique=True, db_index=True)
    arxiv_id = models.CharField(max_length=100, unique=True, db_index=True)
    citation_velocity = models.IntegerField()
    corpus_id = models.IntegerField()
    doi = models.CharField(max_length=100)
    fields_of_study = ArrayField(models.CharField(max_length=70))
    influential_citation_count = models.IntegerField()
    is_open_access = models.BooleanField()
    is_publisher_licensed = models.BooleanField()
    topics = ArrayField(models.CharField(max_length=70))
    url = models.URLField()
    venue = models.CharField(max_length=100)
    year = models.IntegerField()

    # Date when updated from S2
    updated = models.DateTimeField()

    # citation
    citations = ArrayField(models.CharField(max_length=100))
    references = ArrayField(models.CharField(max_length=100))

    # Paper 
    paper = models.OneToOneField(Paper, on_delete=models.CASCADE)

    # define manager
    objects = S2InfoManager.from_queryset(S2InfoQuerySet)() 

# User Specific Models

class UserPreference(models.Model):
    """
    Model for user preference
    """
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, primary_key=True)

    def get_prefer_categories_default():
        return list(settings.PAPERS_MACHINE_LEARNING_CATEGORIES)
    prefer_categories = ArrayField(models.CharField(max_length=100), 
        default=get_prefer_categories_default)

class UserPaper(models.Model):
    """
    Model for Usear and Paper
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    paper = models.ForeignKey(Paper, on_delete=models.CASCADE)

    read_status = models.BooleanField(default=False)
    archive_status = models.BooleanField(default=False)
    star_status = models.BooleanField(default=False)
    pdf_annotation = models.JSONField(null=True)
    tags = ArrayField(models.CharField(max_length=100), default=list, blank=True)
    
    @classmethod
    def get_api_fields(cls):
        all_fileds = ["read_status", "archive_status", "star_status", "pdf_annotation", "tags"]
        return all_fileds
    
    class Meta:
        unique_together = ('user', 'paper',)
