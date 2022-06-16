import shutil
import tempfile
from http import HTTPStatus

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from posts.forms import PostForm
from posts.models import Group, Post

User = get_user_model()

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='testuser')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            id=1,
            author=cls.user,
            text='Тестовый пост 1',
            group=cls.group,
            image=SimpleUploadedFile(
                name='small_1.gif',
                content=(
                    b'\x47\x49\x46\x38\x39\x61\x01\x00'
                    b'\x01\x00\x00\x00\x00\x21\xf9\x04'
                    b'\x01\x0a\x00\x01\x00\x2c\x00\x00'
                    b'\x00\x00\x01\x00\x01\x00\x00\x02'
                    b'\x02\x4c\x01\x00\x3b'
                ),
                content_type='image/gif'
            )
        )
        cls.form = PostForm()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(PostFormTests.user)

    def test_create_post(self):
        """Валидная форма создает запись в Post."""
        posts_count = Post.objects.count()
        small_gif_2 = (
            b'\x47\x49\x46\x38\x39\x61\x01\x00'
            b'\x01\x00\x00\x00\x00\x21\xf9\x04'
            b'\x01\x0a\x00\x01\x00\x2c\x00\x00'
            b'\x00\x00\x01\x00\x01\x00\x00\x02'
            b'\x02\x4c\x01\x00\x3b'
        )
        uploaded = SimpleUploadedFile(
            name='small_2.gif',
            content=small_gif_2,
            content_type='image/gif'
        )
        form_data = {
            'text': 'Тестовый пост 2',
            'group': 1,
            'image': uploaded,
        }
        response = self.authorized_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )
        self.assertRedirects(response, reverse(
            'posts:profile', kwargs={'username': PostFormTests.user}
        ))
        self.assertEqual(Post.objects.count(), posts_count + 1)
        self.assertTrue(
            Post.objects.filter(
                text=form_data['text'],
                group=form_data['group'],
                image=f"posts/{form_data['image']}",
            ).exists()
        )

    def test_edit_post(self):
        """Валидная форма редактирует запись в Post."""
        post = Post.objects.get(pk=1)
        form_data = {
            'text': post.text,
            'group': post.group,
            'image': post.image.name,
        }
        response = self.authorized_client.post(
            reverse('posts:post_edit', kwargs={'post_id': post.id}),
            data=form_data,
            follow=True
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        edited_post = Post.objects.get(pk=post.id)
        self.assertEqual(edited_post.text, form_data['text'])
        self.assertEqual(edited_post.group, form_data['group'])
        self.assertEqual(edited_post.image.name, form_data['image'])
