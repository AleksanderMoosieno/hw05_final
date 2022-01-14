from django.shortcuts import render


def page_not_found(request, exception):
    return render(request, 'core/404.html', {'path': request.path}, status=404)


def server_error(request):
    return render(request, 'core/500.html', status=500)


def permission_denied_view(request, exception):
    template = 'core/403csrf.html'
    return render(request, template)


def permission_denied(request, exception):
    return render(request, 'core/500.html', status=403)