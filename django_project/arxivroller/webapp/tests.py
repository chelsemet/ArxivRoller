from django.http import HttpRequest
from django.test import TestCase, Client, LiveServerTestCase
from django.urls import reverse, resolve
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from selenium.webdriver.firefox.webdriver import WebDriver

from . import views
from .models import Paper

class PaperTest(TestCase):
    def setUp(self):
        Paper.objects.bulk_update_or_create_from_subject(subject="cs.AI,cs.CL,cs.LG", max_results=50)
        pass

    def test_len(self):
        self.assertEqual(len(Paper.objects.all()), 50)

    def test_author_m2m(self):
        for p in Paper.objects.all():
            self.assertTrue(set([a.name for a in p.authors_m2m.all()]) == set(p.authors))


def create_user(username='testuser',password='123456'):
    user = User.objects.create(username=username)
    user.set_password(password)
    user.save()
    return user

def create_user_login(username='testuser',password='123456'):
    user = create_user(username, password)
    client = Client()
    client.login(username=username, password=password)
    return user, client


class HomePageTest(TestCase):
    def setUp(self):
        pass

    def test_root_url_resolves_to_home_page_view(self):
        found = resolve('/')
        self.assertEqual(found.func, views.index)

    def test_home_page_returns_correct_html(self):
        _, client = create_user_login()
        response = client.get('/')
        self.assertIn(b'<title>Arxiv Viewer</title>', response.content)

class MySeleniumTests(StaticLiveServerTestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.selenium = WebDriver()
        cls.selenium.implicitly_wait(10)
        create_user()

    @classmethod
    def tearDownClass(cls):
        cls.selenium.quit()
        super().tearDownClass()

    def test_visit_homepage(self):
        # _, client = create_user_login()
        # response = client.get('/')
        self.selenium.get(
            '%s%s' % (self.live_server_url,  "/")
        )

        self.assertIn("Arxiv Viewer", self.selenium.title)

    def test_login(self):
        self.selenium.get('%s%s' % (self.live_server_url, '/accounts/login/'))
        username_input = self.selenium.find_element_by_name("username")
        username_input.send_keys('testuser')
        password_input = self.selenium.find_element_by_name("password")
        password_input.send_keys('123456')
        self.selenium.find_element_by_name("loginBtn").click()