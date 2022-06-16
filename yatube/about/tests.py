from http import HTTPStatus

from django.test import Client, TestCase
from django.urls import reverse


class AboutViewsTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.templates_page_names = {
            reverse('about:author'): 'about/author.html',
            reverse('about:tech'): 'about/tech.html',
        }

    def setUp(self):
        self.guest_client = Client()

    def test_about_pages_accessible_by_name(self):
        """Страницы About доступны по их адресам."""
        for url in AboutViewsTests.templates_page_names.keys():
            with self.subTest(url=url):
                response = self.guest_client.get(url)
                self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_about_pages_use_correct_templates(self):
        """При запросе к страницам About применяются корректные шаблоны."""
        for url, template in AboutViewsTests.templates_page_names.items():
            with self.subTest(template=template):
                response = self.guest_client.get(url)
                self.assertTemplateUsed(response, template)
