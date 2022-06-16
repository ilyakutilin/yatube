from django.contrib.auth import get_user_model
from django.test import TestCase

from posts.models import Group, Post

User = get_user_model()


class PostModelTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='Тестовый слаг',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост, состоящий более чем из 15 символов',
        )
        cls.model_spec = [
            {
                'field_name': 'text',
                'verbose_name': 'Текст поста',
                'help_text': 'Текст нового поста'
            },
            {
                'field_name': 'pub_date',
                'verbose_name': 'Дата публикации',
                'help_text': ''
            },
            {
                'field_name': 'author',
                'verbose_name': 'Автор поста',
                'help_text': ''
            },
            {
                'field_name': 'group',
                'verbose_name': 'Группа',
                'help_text': 'Группа, к которой будет относиться пост'
            },
        ]

    def test_models_have_correct_object_names(self):
        """Проверяем, что у моделей корректно работает __str__."""
        post = PostModelTest.post
        post_str = str(post)
        post_text = post.text[:15]
        self.assertEqual(post_str, post_text, '__str__ модели Post '
                                              'работает неправильно')

        group = PostModelTest.group
        group_str = str(group)
        self.assertEqual(group_str, group.title, '__str__ модели Group '
                                                 'работает неправильно')

    def test_verbose_name(self):
        for item in PostModelTest.model_spec:
            with self.subTest(item=item):
                self.assertEqual(
                    PostModelTest.post._meta.get_field(
                        item['field_name']
                    ).verbose_name,
                    item['verbose_name']
                )

    def test_help_text(self):
        for item in PostModelTest.model_spec:
            with self.subTest(item=item):
                self.assertEqual(
                    PostModelTest.post._meta.get_field(
                        item['field_name']
                    ).help_text,
                    item['help_text']
                )
