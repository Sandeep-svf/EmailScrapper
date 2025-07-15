# EmailScrapper/views.py
from threading import Thread

from django.shortcuts import render, redirect, get_object_or_404
import pandas as pd
from .scraper import scrape_emails_from_url_list
from scraper.models import EmailScrapeBatch, EmailScrapeJob
from django.http import HttpResponse, JsonResponse
import csv

def home(request):
    batches = EmailScrapeBatch.objects.order_by('-created_at')
    is_running = EmailScrapeBatch.objects.filter(status='in_progress').exists()
    return render(request, 'index.html', {'batches': batches, 'is_running': is_running})

def scraping_progress(request):
    latest_job = EmailScrapeJob.objects.order_by('-created_at').first()
    if not latest_job:
        return JsonResponse({'progress': 0})
    total = latest_job.batch.jobs.count()
    completed = latest_job.batch.jobs.filter(status='completed').count()
    return JsonResponse({
        'completed': completed,
        'total': total,
        'percentage': round((completed / total) * 100, 2) if total else 0
    })

def start_scraping(request):
    if request.method == 'POST' and request.FILES.get('file'):
        if EmailScrapeBatch.objects.filter(status='in_progress').exists():
            return HttpResponse("Scraping already in progress. Please wait.")

        df = pd.read_excel(request.FILES['file'])
        urls = df.iloc[:, 0].dropna().tolist()
        file_name = request.FILES['file'].name

        # Run scraping in a background thread
        thread = Thread(target=scrape_emails_from_url_list, args=(urls,), kwargs={'uploaded_file_name': file_name})
        thread.start()

        return redirect('home')
    return redirect('home')

def batch_detail(request, batch_name):
    batch = get_object_or_404(EmailScrapeBatch, name=batch_name)
    return render(request, 'batch_detail.html', {'batch': batch})

def download_batch_csv(request, batch_name):
    batch = get_object_or_404(EmailScrapeBatch, name=batch_name)
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{batch_name}.csv"'
    writer = csv.writer(response)
    writer.writerow(['URL', 'Status', 'Emails'])
    for job in batch.jobs.all():
        writer.writerow([job.url, job.status, job.emails])
    return response
