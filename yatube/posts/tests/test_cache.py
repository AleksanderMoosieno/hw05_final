from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse

from ..models import Post, User


class CacheTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.no_user_name = 'noUserName'
        cls.user = User.objects.create_user(username=cls.no_user_name)
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост',
        )

    def test_cache_on_index_page_works_correct(self):
        """Кэширование данных на главной странице работает корректно."""
        response = self.client.get(reverse('posts:index'))
        cached_content = response.content
        Post.objects.all().delete()
        response = self.client.get(reverse('posts:index'))
        cached_content_after_delete = response.content
        self.assertEqual(
            cached_content,
            cached_content_after_delete,
            'Кэширование работает некорректно.'
        )
        cache.clear()
        response = self.client.get(reverse('posts:index'))
        self.assertNotEqual(
            cached_content,
            response.content,
            'Кэширование после очистки работает некорректно'
        )
