from django.shortcuts import render,get_object_or_404
from django.urls import reverse
from django.template import loader, RequestContext
from django.http import Http404, HttpResponse, HttpResponseRedirect, HttpResponseBadRequest, FileResponse
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import F
from django.views import generic
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User

from .models import Paper, UserPreference
from .form import ProfileForm

import requests
import re
from bs4 import BeautifulSoup
import json

@login_required(login_url='/accounts/login_require')
def user_profile(request):
    return render(request, 'accounts/profile.html')

@login_required(login_url='/accounts/login_require')
def user_setting(request):
    if request.method == "POST":
        form = ProfileForm(request.POST)
        if form.is_valid():
            user = request.user
            # print(request.POST)
            # print(form.cleaned_data)
            if form.cleaned_data['email'] != '':
                user.email = form.cleaned_data['email']
            user.save()
            form = ProfileForm()
    else:
        form = ProfileForm()
    return render(request, 'accounts/setting.html', {'form': form})


@login_required(login_url='/accounts/login_require')
def index(request):
    return render(request, 'index.html')

@login_required(login_url='/accounts/login_require')
def graphvis(request):
    return render(request, 'graphvis.html')


@login_required(login_url='/accounts/login_require')
def update(request):
    # raise Http404("Question does not exist")
    try:
        if request.method == "POST":
            subject = request.POST["subject"].strip()
            max_results = request.POST["max_results"] if "max_results" in request.POST else 100
            Paper.objects.bulk_update_or_create_from_subject(subject=subject, max_results=max_results)
            # print("Updating Papers")
    except:
        raise HttpResponseBadRequest("Can not make update")
    # context = {'latest_paper_list': Paper.objects.all().reverse()[:20]}
    return HttpResponse(status=201)


@login_required(login_url='/accounts/login_require')
def scapeArxivVanity(request):
    if request.method == "GET":
        arxiv_id = request.GET["arxiv_id"].strip()
        print(arxiv_id)
        page = requests.get(f"http://www.arxiv-vanity.com/papers/{arxiv_id}").text
        style_url = re.findall(r'https://media.arxiv-vanity.com/render-output/\d+/index.css', page)[0]
        style = requests.get(style_url).text.replace("/*# sourceMappingURL=/index.css.map */","")
        soup = BeautifulSoup(page, 'html.parser')
        main_html = soup.find_all("div", class_="ltx_page_main")[0].prettify()
        main_html = main_html.replace('href="/papers/','href="/papers/?arxiv_id=')
        main_html = main_html.replace('target="_blank"',"")

        return HttpResponse(json.dumps({"style": style, "main_html":main_html}))
    else:
        raise HttpResponseBadRequest("Can not make update")

# @login_required(login_url='/accounts/login_require')
# def scapePDF(request):
#     if request.method == "GET":
#         url = request.GET["url"].strip()
#         response = requests.get(url)
#         print(url)
#         return FileResponse(response.content, content_type='application/pdf')
#     else:
#         raise HttpResponseBadRequest("Can not make update")

