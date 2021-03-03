from django_extensions.management.jobs import DailyJob

class Job(DailyJob):
    help = "Django Daily Job For Updating Arxiv Papers"

    def execute(self):
        from django.core import management
        management.call_command("runscript scrape_arxiv --traceback --script-args ml eess stat cs")