from django.shortcuts import render

def index(request):
    return render(request, 'index.html')

def privacy_policy(request):
    return render(request, 'privacy_policy.html')

def terms_of_service(request):
    return render(request, 'terms_of_service.html')
