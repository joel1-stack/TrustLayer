from django.shortcuts import render


def docs_view(request):
    return render(request, 'admin_dashboard/docs.html')
