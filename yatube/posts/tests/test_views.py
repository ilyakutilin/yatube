import shutil
import tempfile

from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from posts.models import Comment, Follow, Group, Post

User = get_user_model()

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostPagesTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user1 = User.objects.create_user(username='testuser1')
        cls.user2 = User.objects.create_user(username='testuser2')
        cls.user3 = User.objects.create_user(username='testuser3')
        cls.group1 = Group.objects.create(
            title='Тестовая группа 1',
            slug='test-slug-1',
            description='Тестовое описание',
        )
        cls.group2 = Group.objects.create(
            title='Тестовая группа 2',
            slug='test-slug-2',
            description='Тестовое описание',
        )
        number_of_posts = 12
        posts = []
        for post_id in range(1, number_of_posts + 1):
            post = Post(
                id=post_id,
                author=cls.user2 if post_id % 2 == 0 else cls.user1,
                text=f'Тестовый пост {post_id}',
                group=cls.group2 if post_id % 2 == 0 else cls.group1,
            )
            posts.append(post)
        Post.objects.bulk_create(posts)
        cls.templates_page_names = {
            reverse('posts:index'): 'posts/index.html',
            reverse('posts:group_posts', kwargs={'slug': cls.group1.slug}): (
                'posts/group_list.html'
            ),
            reverse(
                'posts:profile',
                kwargs={'username': cls.user1.username}
            ): ('posts/profile.html'),
            reverse(
                'posts:post_detail',
                kwargs={'post_id': Post.objects.get(pk=3).id}
            ): ('posts/post_detail.html'),
            reverse(
                'posts:post_edit',
                kwargs={'post_id': Post.objects.get(pk=3).id}
            ): ('posts/create_post.html'),
            reverse('posts:post_create'): 'posts/create_post.html',
        }

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        cache.clear()
        self.guest_client = Client()
        self.authorized_client_1 = Client()
        self.authorized_client_1.force_login(PostPagesTests.user1)
        self.authorized_client_2 = Client()
        self.authorized_client_2.force_login(PostPagesTests.user2)

    # Проверка шаблонов
    def test_pages_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        for reverse_name, template in (
            PostPagesTests.templates_page_names.items()
        ):
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client_1.get(reverse_name)
                self.assertTemplateUsed(response, template)

    # Проверка контекста главной страницы, страниц группы и профиля
    def test_index_has_correct_context(self):
        """Шаблон index сформирован с правильным контекстом"""
        response = self.guest_client.get(reverse('posts:index'))
        self.assertContains(response, 'Тестовый пост', count=10)

    def test_group_posts_has_correct_context(self):
        """Шаблон group_posts сформирован с правильным контекстом"""
        group = PostPagesTests.group2
        response = self.guest_client.get(
            reverse('posts:group_posts', kwargs={'slug': group.slug})
        )
        page_objects = response.context['page_obj']
        for object in page_objects:
            self.assertEqual(str(object.group), group.title)

    def test_profile_has_correct_context(self):
        """Шаблон profile сформирован с правильным контекстом"""
        user = PostPagesTests.user2
        response = self.guest_client.get(
            reverse('posts:profile', kwargs={'username': user.username})
        )
        page_objects = response.context['page_obj']
        for object in page_objects:
            self.assertEqual(str(object.author), user.username)

    # Тестирование страниц просмотра поста, его создания и редактирования
    def test_post_detail_correct_context(self):
        """Шаблон post_detail сформирован с правильным контекстом"""
        post = Post.objects.get(pk=1)
        response = self.guest_client.get(
            reverse('posts:post_detail', kwargs={'post_id': post.id})
        )
        context = response.context['post']
        self.assertEqual(context.text, post.text)
        self.assertEqual(context.id, post.id)
        self.assertEqual(context.author, post.author)
        self.assertEqual(context.group, post.group)

    def test_post_create_correct_context(self):
        """Шаблон post_create сформирован с правильным контекстом"""
        response = self.authorized_client_1.get(reverse('posts:post_create'))
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.models.ModelChoiceField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context['form'].fields[value]
                self.assertIsInstance(form_field, expected)

    def test_created_post_shown_where_needed(self):
        """Созданный пост с указанием группы появляется на главной странице,
        на странице группы и в профайле пользователя.
        """
        post = Post.objects.create(
            author=PostPagesTests.user1,
            text='Тестовый пост 100',
            group=PostPagesTests.group1,
        )
        reverses = [
            reverse('posts:index'),
            reverse('posts:group_posts', kwargs={'slug': post.group.slug}),
            reverse('posts:profile', kwargs={'username': post.author}),
        ]
        for reverse_name in reverses:
            with self.subTest(reverse_name=reverse_name):
                response = self.guest_client.get(reverse_name)
                self.assertContains(response, post.text, count=1)

    def test_created_post_not_shown_where_not_needed(self):
        """Созданный пост с указанием группы не появляется
        на странице другой группы.
        """
        post = Post.objects.create(
            author=PostPagesTests.user1,
            text='Тестовый пост 101',
            group=PostPagesTests.group1,
        )
        response = self.guest_client.get(reverse(
            'posts:group_posts', kwargs={'slug': PostPagesTests.group2.slug})
        )
        self.assertNotContains(response, post.text)

    def test_post_edit_correct_form_initials(self):
        """Контекст post_edit сформирован верно"""
        post = Post.objects.get(id=5)
        response = self.authorized_client_1.get(
            reverse(
                'posts:post_edit',
                kwargs={'post_id': post.id}
            )
        )
        form = response.context['form']
        text_inital = form.get_initial_for_field(form.fields['text'], 'text')
        self.assertEqual(text_inital, post.text)
        group_initial = form.get_initial_for_field(
            form.fields['group'], 'group'
        )
        self.assertEqual(group_initial, post.group.id)

    def test_picture_in_post_shown_where_needed(self):
        """Картинка в посте показывается на главной странице, на страницах
        профиля и группы
        """
        # Создаем новый пост с картинкой
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x01\x00'
            b'\x01\x00\x00\x00\x00\x21\xf9\x04'
            b'\x01\x0a\x00\x01\x00\x2c\x00\x00'
            b'\x00\x00\x01\x00\x01\x00\x00\x02'
            b'\x02\x4c\x01\x00\x3b'
        )
        uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )
        post_with_pic = Post.objects.create(
            author=PostPagesTests.user1,
            text='Тестовый пост с картинкой',
            group=PostPagesTests.group1,
            image=uploaded,
        )
        urls_context = {
            reverse('posts:index'): 'page_obj',
            reverse(
                'posts:group_posts',
                kwargs={'slug': post_with_pic.group.slug},
            ): 'page_obj',
            reverse(
                'posts:profile',
                kwargs={'username': post_with_pic.author.username}
            ): 'page_obj',
        }
        for url, context in urls_context.items():
            with self.subTest(url):
                response = self.guest_client.get(url)
                first_object = response.context[context][0]
                self.assertEqual(
                    first_object.image,
                    post_with_pic.image
                )
        post_url = reverse(
            'posts:post_detail',
            kwargs={'post_id': post_with_pic.id}
        )
        response = self.guest_client.get(post_url)
        post_object = response.context['post']
        self.assertEqual(
            post_object.image,
            post_with_pic.image
        )

    def test_comment(self):
        """Комментарий к посту появляется на странице поста"""
        post = Post.objects.get(id=3)
        comment = Comment.objects.create(
            post=post,
            author=post.author,
            text='Тестовый комментарий 2',
        )
        response = self.authorized_client_1.get(
            reverse('posts:post_detail', kwargs={'post_id': post.id})
        )
        self.assertContains(response, comment.text, count=1)

    def test_authorized_user_can_subscribe(self):
        """Авторизованный пользователь может подписываться
        на других пользователей
        """
        # Считаем объекты Follow
        follow_count = Follow.objects.count()
        # Автор, на которого подписываемся - testuser1
        author = PostPagesTests.user1
        url = reverse('posts:profile_follow', kwargs={'username': author})
        # Авторизованный пользователь - testuser2
        self.authorized_client_2.get(url)
        # Проверяем, что после перехода по url создается новый объект Follow
        self.assertEqual(Follow.objects.count(), follow_count + 1)
        self.assertTrue(
            Follow.objects.filter(
                user=PostPagesTests.user2.pk,
                author=author.pk,
            ).exists()
        )

    def test_authorized_user_can_unsubscribe(self):
        """Авторизованный пользователь может удалять
        других пользователей из подписок
        """
        # Автор, на которого подписываемся - testuser1
        author = PostPagesTests.user1
        # Создаем новую подписку
        Follow.objects.create(
            user=PostPagesTests.user2,
            author=author,
        )
        # Считаем объекты Follow
        follow_count = Follow.objects.count()
        url = reverse('posts:profile_unfollow', kwargs={'username': author})
        # Авторизованный пользователь - testuser2
        self.authorized_client_2.get(url)
        # Проверяем, что объект Follow удален (подписка отменена)
        self.assertEqual(Follow.objects.count(), follow_count - 1)
        self.assertFalse(
            Follow.objects.filter(
                user=PostPagesTests.user2.pk,
                author=author.pk,
            ).exists()
        )

    def test_new_author_post_is_shown_for_subscribers_only(self):
        """Новая запись пользователя появляется в ленте тех,
        кто на него подписан, и не появляется в ленте тех,
        кто на него не подписан
        """
        # Автор, на которого подписываются - testuser3
        author = PostPagesTests.user3
        # Создаем новую подписку - testuser1 подписан на testuser3
        Follow.objects.create(
            user=PostPagesTests.user1,
            author=author,
        )
        # Создаем пост автора (user3)
        post = Post.objects.create(
            author=author,
            text='Тестовый пост 123',
        )
        url = reverse('posts:follow_index')
        # Проверка того, что новый пост автора появился в ленте подписчика
        response_subscriber = self.authorized_client_1.get(url)
        self.assertContains(response_subscriber, post.text, count=1)
        # Проверка того, что новый пост автора не появился в ленте
        # не подписанного на него пользователя
        response_not_subscriber = self.authorized_client_2.get(url)
        self.assertNotContains(response_not_subscriber, post.text)


class PaginatorViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user1 = User.objects.create_user(username='testuser1')
        cls.user2 = User.objects.create_user(username='testuser2')
        cls.group1 = Group.objects.create(
            title='Тестовая группа 1',
            slug='test-slug-1',
            description='Тестовое описание',
        )
        cls.group2 = Group.objects.create(
            title='Тестовая группа 2',
            slug='test-slug-2',
            description='Тестовое описание',
        )
        number_of_posts = 28
        posts = []
        for post_id in range(1, number_of_posts + 1):
            post = Post(
                id=post_id,
                author=cls.user2 if post_id % 2 == 0 else cls.user1,
                text=f'Тестовый пост {post_id}',
                group=cls.group2 if post_id % 2 == 0 else cls.group1,
            )
            posts.append(post)
        Post.objects.bulk_create(posts)

    def setUp(self):
        cache.clear()
        self.guest_client = Client()

    def test_first_page_contains_ten_records(self):
        """Первая страница index, group_posts и profile отображает 10 постов"""
        pages_posts = {
            reverse('posts:index'): 10,
            reverse('posts:group_posts', kwargs={'slug': 'test-slug-1'}): 10,
            reverse('posts:profile', kwargs={'username': 'testuser1'}): 10,
        }
        for page, number_of_posts in pages_posts.items():
            with self.subTest(page=page):
                response = self.guest_client.get(page)
                self.assertEqual(
                    len(response.context['page_obj']), number_of_posts
                )

    def test_last_page_contains_n_records(self):
        """Последняя страница index, group_posts и profile отображает
        N постов
        """
        pages_posts = {
            reverse('posts:index') + '?page=3': 8,
            reverse('posts:group_posts',
                    kwargs={'slug': 'test-slug-1'}) + '?page=2': 4,
            reverse('posts:profile',
                    kwargs={'username': 'testuser1'}) + '?page=2': 4,
        }
        for page, number_of_posts in pages_posts.items():
            with self.subTest(page=page):
                response = self.guest_client.get(page)
                self.assertEqual(
                    len(response.context['page_obj']), number_of_posts
                )


class CacheViewTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='testuser')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        number_of_posts = 2
        posts = []
        for post_id in range(1, number_of_posts + 1):
            post = Post(
                id=post_id,
                author=cls.user,
                text=f'Тестовый пост {post_id}',
                group=cls.group,
            )
            posts.append(post)
        Post.objects.bulk_create(posts)

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(CacheViewTest.user)

    def test_cache_index(self):
        """Кеш на главной странице работает корректно"""
        first_response = self.authorized_client.get(reverse('posts:index'))
        post = Post.objects.get(id=1)
        post.delete()
        cached_response = self.authorized_client.get(reverse('posts:index'))
        self.assertEqual(first_response.content, cached_response.content)
        cache.clear()
        clean_response = self.authorized_client.get(reverse('posts:index'))
        self.assertNotEqual(first_response.content, clean_response.content)
