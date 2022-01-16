import shutil
import tempfile

from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.core.cache import cache

from ..models import Group, Post

User = get_user_model()

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.test_user = User.objects.create(
            username='test_username',
            email='testmail@gmail.com',
            password='Qwerty123',
        )
        cls.group = Group.objects.create(
            title='Тестовый заголовок',
            slug='test-group',
            description='Тестовое описание',
        )
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )
        cls.post = Post.objects.create(
            author=cls.test_user,
            group=cls.group,
            text='Тестовый текст',
            image=uploaded,
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.test_user)

    def test_pages_use_correct_templates(self):
        """URL-адрес использует корректный шаблон."""
        cache.clear()
        templates_pages_names = {
            reverse('posts:index'): 'posts/index.html',
            reverse('posts:group_list', args=[PostViewsTest.group.slug]):
            'posts/group_list.html',
            reverse('posts:profile',
                    args=[PostViewsTest.test_user.username]):
            'posts/profile.html',
            reverse('posts:post_detail', args=[PostViewsTest.post.id]):
            'posts/post_detail.html',
            reverse('posts:post_edit', args=[PostViewsTest.post.id]):
            'posts/create_post.html',
            reverse('posts:post_create'): 'posts/create_post.html',
        }
        for reverse_name, template in templates_pages_names.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def test_new_post_appears_on_pages(self):
        """Новый пост отображается на страницах index, group, profile"""
        cache.clear()
        expected_context = self.post
        urls_pages = [
            reverse('posts:index'),
            reverse('posts:group_list', args=[PostViewsTest.group.slug]),
            reverse('posts:profile', args=[PostViewsTest.test_user.username]),
        ]
        for url in urls_pages:
            with self.subTest(url=url):
                response = self.authorized_client.get(url)
                self.assertEqual(len(response.context['page_obj']), 1)
                current_context = response.context['page_obj'][0]
                self.assertEqual(current_context, expected_context)

    def test_new_post_does_not_appear_in_other_group(self):
        """Новый пост не отображается не в своей группе."""
        other_group = Group.objects.create(
            title='Другой тестовый заголовок',
            slug='other-test-group',
            description='Другое тестовое описание',
        )
        other_group_url = reverse('posts:group_list', args=[other_group.slug])
        response = self.authorized_client.get(other_group_url)
        self.assertNotIn(self.post, response.context['page_obj'])

    def test_index_page_uses_correct_context(self):
        """Шаблон главной страницы сформирован с правильным контекстом."""
        cache.clear()
        response = self.authorized_client.get(reverse('posts:index'))
        index_post = response.context['page_obj'][0]
        self.check_post_context_on_page(index_post)

    def check_post_context_on_page(self, first_object):
        self.assertEqual(first_object.text, self.post.text)
        self.assertEqual(first_object.author, self.post.author)
        self.assertEqual(first_object.group, self.post.group)
        self.assertTrue(first_object.image, self.post.image)

    def check_group_context_on_page(self, second_object):
        self.assertEqual(second_object.title, self.group.title)
        self.assertEqual(second_object.description, self.group.description)
        self.assertEqual(second_object.slug, self.group.slug)

    def test_profile_page_uses_correct_context(self):
        """Шаблон страницы пользователя сформирован с правильным контекстом."""
        profile_page = reverse('posts:profile',
                               args=[PostViewsTest.test_user.username])
        response = self.authorized_client.get(profile_page)
        profile_post = response.context['page_obj'][0]
        self.check_post_context_on_page(profile_post)

    def test_group_page_uses_correct_context(self):
        """Шаблон страницы группы сформирован с правильным контекстом."""
        group_page = reverse('posts:group_list',
                             args=[PostViewsTest.group.slug])
        response = self.authorized_client.get(group_page)
        response_group = response.context.get('group')
        response_post = response.context['page_obj'][0]
        self.check_post_context_on_page(response_post)
        self.check_group_context_on_page(response_group)

    def test_post_detail_page_uses_correct_context(self):
        """Шаблон страницы поста сформирован с правильным контекстом."""
        post_detail_page = reverse('posts:post_detail',
                                   args=[PostViewsTest.post.id])
        response = self.authorized_client.get(post_detail_page)
        response_post = response.context.get('post')
        self.check_post_context_on_page(response_post)
        self.assertEqual(self.post, response_post)

    def test_create_and_edit_post_pages_use_correct_context(self):
        """Шаблоны страниц создания и редактирования поста
        сформированы с правильным контекстом."""
        url_pages = [reverse('posts:post_edit', args=[PostViewsTest.post.id]),
                     reverse('posts:post_create')]
        for url in url_pages:
            response = self.authorized_client.get(url)
            form_fields = {
                'text': forms.fields.CharField,
                'group': forms.models.ModelChoiceField,
            }
            for value, expected in form_fields.items():
                with self.subTest(value=value):
                    form_field = response.context.get('form').fields.get(value)
                    self.assertIsInstance(form_field, expected)


class PaginatorViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.test_user = User.objects.create(
            username='test_username',
            email='testmail@gmail.com',
            password='Qwerty123',
        )
        cls.authorized_client = Client()
        cls.authorized_client.force_login(cls.test_user)
        cls.group = Group.objects.create(
            title='Тестовый заголовок',
            slug='test-group',
            description='Тестовое описание',
        )
        cls.posts = Post.objects.bulk_create([
            Post(
                author=cls.test_user,
                group=cls.group,
                text=f'Тестовый текст поста номер {item}',
            )
            for item in range(settings.CONST + 3)
        ])

    def test_paginator_for_index_profile_group(self):
        """Паджинатор на страницах index, profile, group работает корректно."""
        cache.clear()
        first_page_len = settings.CONST
        second_page_len = len(self.posts) - settings.CONST
        if second_page_len > settings.CONST:
            second_page_len = settings.CONST
        else:
            second_page_len = len(self.posts) - settings.CONST

        context = {
            reverse('posts:index'): first_page_len,
            reverse('posts:index') + '?page=2': second_page_len,
            reverse('posts:group_list', args=[PaginatorViewsTest.group.slug]):
            first_page_len,
            reverse('posts:group_list', args=[PaginatorViewsTest.group.slug])
            + '?page=2': second_page_len,
            reverse('posts:profile',
                    args=[PaginatorViewsTest.test_user.username]):
            first_page_len,
            reverse('posts:profile',
                    args=[PaginatorViewsTest.test_user.username]) + '?page=2':
            second_page_len,
        }
        for requested_page, page_len in context.items():
            with self.subTest(requested_page=requested_page):
                response = self.authorized_client.get(requested_page)
                self.assertEqual(len(response.context['page_obj']), page_len)


class PagesError(TestCase):
    def setUp(self):
        self.client = Client()

    def test_404_page(self):
        """Тест кастомной 404 ошибки."""
        response = self.client.get('/unexisting_page/')
        self.assertEqual(response.status_code, 404)
        self.assertTemplateUsed(response, 'core/404.html')
