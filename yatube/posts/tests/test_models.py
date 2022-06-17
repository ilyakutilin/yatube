from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.test import TestCase

from posts.models import Comment, Follow, Group, Post

User = get_user_model()


class ModelTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user1 = User.objects.create_user(username='user1')
        cls.user2 = User.objects.create_user(username='user2')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='Тестовый слаг',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user1,
            text='Тестовый пост, состоящий более чем из 15 символов',
        )
        cls.comment = Comment.objects.create(
            post=cls.post,
            author=cls.user2,
            text='Тестовый комментарий',
        )
        cls.follow = Follow.objects.create(
            user=cls.user2,
            author=cls.user1,
        )
        cls.str_spec = {
            cls.post: cls.post.text[:15],
            cls.group: cls.group.title,
            cls.comment: cls.comment.text[:15]
        }
        cls.post_model_spec = (
            ('text', 'Текст поста', 'Текст нового поста'),
            ('pub_date', 'Дата публикации', ''),
            ('author', 'Автор поста', ''),
            ('group', 'Группа', 'Группа, к которой будет относиться пост'),
        )
        cls.comment_model_spec = (
            ('post', 'Пост', 'Комментируемый пост'),
            ('author', 'Автор поста', 'Автор комментируемого поста'),
            ('text', 'Текст комментария', 'Текст нового комментария'),
            ('created', 'Дата комментария', ''),
        )
        cls.follow_model_spec = (
            (
                'user',
                'Подписчик',
                'Пользователь, который подписывается на автора'
            ),
            ('author', 'Автор', 'Автор, на которого подписываются'),
        )

    def test_models_have_correct_object_names(self):
        """Проверяем, что у моделей корректно работает __str__."""
        for model_object, expected_str in ModelTest.str_spec.items():
            with self.subTest(model_object=model_object):
                self.assertEqual(str(model_object), expected_str)

    def test_post_verbose_and_help_text_names(self):
        for field, verbose_name, help_text in ModelTest.post_model_spec:
            with self.subTest(field=field):
                self.assertEqual(
                    ModelTest.post._meta.get_field(field).verbose_name,
                    verbose_name
                )
                self.assertEqual(
                    ModelTest.post._meta.get_field(field).help_text,
                    help_text
                )

    def test_comment_verbose_and_help_text_names(self):
        for field, verbose_name, help_text in ModelTest.comment_model_spec:
            with self.subTest(field=field):
                self.assertEqual(
                    ModelTest.comment._meta.get_field(field).verbose_name,
                    verbose_name
                )
                self.assertEqual(
                    ModelTest.comment._meta.get_field(field).help_text,
                    help_text
                )

    def test_follow_verbose_and_help_text_names(self):
        for field, verbose_name, help_text in ModelTest.follow_model_spec:
            with self.subTest(field=field):
                self.assertEqual(
                    ModelTest.follow._meta.get_field(field).verbose_name,
                    verbose_name
                )
                self.assertEqual(
                    ModelTest.follow._meta.get_field(field).help_text,
                    help_text
                )

    def test_no_self_follow(self):
        user = ModelTest.user1
        constraint_name = "posts_follow_prevent_self_follow"
        with self.assertRaisesMessage(IntegrityError, constraint_name):
            Follow.objects.create(user=user, author=user)
