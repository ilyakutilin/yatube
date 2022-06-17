from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import Client, TestCase

from posts.models import Comment, Group, Post

User = get_user_model()


class PostURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Создаем двух пользователей: один - автор поста,
        # второй - просто авторизованный пользователь (не автор поста)
        cls.author = User.objects.create_user(username='author')
        cls.notauthor = User.objects.create_user(username='notauthor')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            id=123,
            author=cls.author,
            text='Тестовый пост',
            group=cls.group,
        )
        cls.comment = Comment.objects.create(
            post=cls.post,
            author=cls.author,
            text='Тестовый комментарий',
        )
        # Список URL: первые 5 - публичные, последние 2 - требуют авторизации
        cls.urls = (
            ('/', 'posts/index.html'),
            (f'/group/{cls.group.slug}/', 'posts/group_list.html'),
            (f'/profile/{cls.author.username}/', 'posts/profile.html'),
            (f'/profile/{cls.notauthor.username}/', 'posts/profile.html'),
            (f'/posts/{cls.post.id}/', 'posts/post_detail.html'),
            (f'/posts/{cls.post.id}/edit/', 'posts/create_post.html'),
            ('/create/', 'posts/create_post.html'),
        )
        cls.unauth_redirects = {
            '/create/': '/auth/login/?next=/create/',
            f'/posts/{cls.post.id}/edit/': (f'/auth/login/?next=/posts/'
                                            f'{cls.post.id}/edit/'),
            f'/posts/{cls.post.id}/comment/': (f'/auth/login/?next=/posts/'
                                               f'{cls.post.id}/comment/'),
        }
        cls.follow_redirects = {
            '/profile/author/follow/': (f'/profile/{cls.author.username}/'
                                        'follow/success/'),
            '/profile/author/unfollow/': (f'/profile/{cls.author.username}/'
                                          'unfollow/success/'),
        }

    def setUp(self):
        cache.clear()
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(PostURLTests.author)
        self.authorized_client_na = Client()
        self.authorized_client_na.force_login(PostURLTests.notauthor)

    # Проверка общедоступных страниц
    def test_public_urls_exist_at_desired_locations(self):
        """Общедоступные страницы доступны любому пользователю."""
        # Тестируем только первые 5 URL из списка (публичные)
        for public_url, *_ in PostURLTests.urls[:5]:
            with self.subTest(public_url=public_url):
                response = self.guest_client.get(public_url)
                self.assertEqual(response.status_code, HTTPStatus.OK)

    # Проверка вызываемых шаблонов для каждого адреса
    def test_urls_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        for url, template in PostURLTests.urls:
            with self.subTest(url=url):
                response = self.authorized_client.get(url)
                self.assertTemplateUsed(response, template)

    def test_nonexistent_page_returns_404(self):
        """Несуществующая страница возвращает код 404."""
        response = self.guest_client.get('/unexisting_page/')
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
        self.assertTemplateUsed(response, 'core/404.html')

    # Проверка Создания новой записи
    def test_create_post_url_exists_at_desired_location(self):
        """Страница /create/ доступна авторизованному пользователю."""
        response = self.authorized_client_na.get('/create/')
        self.assertEqual(response.status_code, HTTPStatus.OK)

    # Проверка Редактирования записи
    # Если редактировать запись пытается ее автор
    def test_edit_post_url_exists_at_desired_location_author(self):
        """Страница /posts/post_id/edit/ доступна автору поста."""
        response = self.authorized_client.get(
            f'/posts/{PostURLTests.post.id}/edit/'
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)

    # Если редактировать запись пытается не ее автор
    def test_edit_post_url_redirect_nonauthor_to_post_view(self):
        """Страница /posts/post_id/edit/ перенаправит пользователя,
        не являющегося автором поста, на страницу просмотра поста.
        """
        response = self.authorized_client_na.get(
            f'/posts/{PostURLTests.post.id}/edit/'
        )
        self.assertRedirects(response, f'/posts/{PostURLTests.post.id}/')

    # Проверка редиректа при комментировании
    def test_comment_post_url_redirect_to_post_view(self):
        """Страница /posts/post_id/comment/ перенаправит любого
        авторизованного пользователя на страницу просмотра поста.
        """
        response = self.authorized_client_na.get(
            f'/posts/{PostURLTests.post.id}/comment/'
        )
        self.assertRedirects(response, f'/posts/{PostURLTests.post.id}/')

    # Проверка редиректов для неавторизованного пользователя
    def test_urls_redirect_anonymous_on_auth_login(self):
        """Анонимные пользователи перенаправляются на страницу логина"""
        for url, expected_redirect in PostURLTests.unauth_redirects.items():
            with self.subTest(url=url):
                response = self.guest_client.get(url)
                self.assertRedirects(response, expected_redirect)

    # Проверка редиректов подписки и отписки
    def test_follow_and_unfollow_redirect_to_info_pages(self):
        """Подписка на автора и отписка от него
        перенаправляет на соответствующую информационную страницу"""
        for url, expected_redirect in PostURLTests.follow_redirects.items():
            with self.subTest(url=url):
                response = self.authorized_client_na.get(url)
                self.assertRedirects(response, expected_redirect)
