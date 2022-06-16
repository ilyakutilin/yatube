from django.core.paginator import Paginator

POST_LIMIT = 10


def pagination(request, objects):
    paginator = Paginator(objects, POST_LIMIT)
    page_number = request.GET.get('page')
    return paginator.get_page(page_number)
