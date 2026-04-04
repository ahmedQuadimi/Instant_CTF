from django.shortcuts import render


def home(request):
    return render(request, "home.html")


def dev_index(request):
    return render(request, "dev/index.html")


def dev_components(request):
    return render(request, "dev/components.html")


def dev_auth(request):
    return render(request, "dev/auth.html")
