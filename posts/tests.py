import tempfile
import time

from django.test import Client, TestCase
from django.urls import reverse
from PIL import Image

from .models import Comment, Follow, Group, Post, User


class TestStringMethods(TestCase):
    def setUp(self):
        self.client = Client()
        self.auth_client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@mail.ru'
        )
        self.user2 = User.objects.create_user(
            username='testuser2',
            email='test@mail2.ru'
        )
        self.author_user = User.objects.create_user(
            username='author_user',
            email='author@mail.ru'
        )
        self.auth_client.force_login(self.user)
        self.post_text = 'Blah blah lah'
        self.group = Group.objects.create(
            slug='fishing',
            title='sea fishing',
            description='bla-bla-bla'
        )

    def test_new_profile(self):
        response = self.client.get(
            reverse('profile', args=(self.user.username,)),
            follow=True
        )
        self.assertEqual(response.status_code, 200)

    def test_auth_user_post(self):
        response = self.auth_client.post(
            reverse('new_post'),
            {'group': self.group.id, 'text': self.post_text},
            follow=True
        )
        posts_count = Post.objects.count()
        self.assertEquals(response.status_code, 200)
        self.assertEquals(posts_count, 1)
        added_post = Post.objects.first()
        self.assertEquals(added_post.group, self.group)
        self.assertEquals(added_post.author, self.user)
        self.assertEquals(added_post.text, self.post_text)

    def test_unauth_user_post(self):
        response = self.client.post(
            reverse('new_post'),
            {'group': self.group.id, 'text': self.post_text},
            follow=True
        )
        posts_num = Post.objects.count()
        self.assertEquals(posts_num, 0)
        self.assertRedirects(
            response,
            # по другому не знаю как это записать
            reverse('login') + '?next=' + reverse('new_post'),
            status_code=302,
            target_status_code=200,
            msg_prefix='',
            fetch_redirect_response=True
        )

    # Проверка доступности поста на страницах
    def is_in_page(self, curl, tuser, tgroup, ttext):
        response = self.auth_client.get(curl, follow=True)
        if 'paginator' in response.context:
            rc = response.context['page'].object_list[0]
        else:
            rc = response.context['post']
        self.assertEquals(rc.text, ttext)
        self.assertEquals(rc.author, tuser)
        self.assertEquals(rc.group, tgroup)

    def test_post_available_everywhere(self):
        Post.objects.create(
            author=self.user,
            group=self.group,
            text=self.post_text
        )
        urls = [
            reverse('index'),
            reverse('profile', args=[self.user.username]),
            reverse('group_posts', kwargs={'slug': self.group.slug}),
            reverse(
                'post',
                kwargs={'username': self.user.username, 'post_id': 1}
            )
        ]
        for url in urls:
            self.is_in_page(url, self.user, self.group, self.post_text)

    def test_post_modified(self):
        # Добавляем новый пост в группу
        Post.objects.create(
            author=self.user,
            group=self.group,
            text=self.post_text
        )

        # Редактируем пост и меняем группу публикации
        new_post = ('Новый пост на канале, подписываемся!')

        new_group = Group.objects.create(
            slug='snorcling',
            title='water activity',
            description='new bla-bla-bla'
        )

        self.auth_client.post(
            reverse(
                'post_edit',
                kwargs={'username': self.user.username, 'post_id': 1}
            ),
            {'text': new_post, 'group': new_group.id},
            follow=True
        )

        # Проверяем, что отредактированный пост доступен на нужных страницах
        urls = [
            reverse('index'),
            reverse('profile', args=[self.user.username]),
            reverse('group_posts', kwargs={'slug': new_group.slug}),
            reverse(
                'post',
                kwargs={'username': self.user.username, 'post_id': 1}
            )
        ]
        for url in urls:
            self.is_in_page(url, self.user, new_group, new_post)

        posts_in_old_group = Post.objects.filter(
            author=self.user,
            group=self.group
        ).count()

        # Проверяем, что пост исчез из старой группы в БД
        self.assertEquals(posts_in_old_group, 0)

        # Проверяем, что пост исчез из старой группы на странице
        response = self.client.get(
            reverse('group_posts', kwargs={'slug': self.group.slug}),
            follow=True
        )
        posts_in_old_group = response.context['page'].object_list.count()
        self.assertEquals(posts_in_old_group, 0)

    def test_404_return(self):
        url = '/not_existing_file/'
        response = self.client.get(url, follow=True)
        self.assertEquals(response.status_code, 404)

    def test_img(self):
        # Создаем пост без картинки
        Post.objects.create(
            author=self.user,
            group=self.group,
            text=self.post_text
        )

        # Редактируем пост и добавляем картинку
        image_test = Image.new('RGB', (60, 30), color=(73, 109, 137))
        image_test.save('image_test.png')

        with open('image_test.png', 'rb') as img:
            response = self.auth_client.post(
                reverse(
                    'post_edit',
                    kwargs={'username': self.user.username, 'post_id': 1}
                ),
                {'text': self.post_text, 'group': self.group.id, 'image': img},
                follow=True
            )

            # Проверяем что пост успешно добавился
            self.assertEquals(response.status_code, 200)
            posts_count = Post.objects.count()
            self.assertEquals(posts_count, 1)

            # Проверяем, что <img> есть на страницах
            urls = [
                reverse('index'),
                reverse('profile', args=[self.user.username]),
                reverse('group_posts', kwargs={'slug': self.group.slug}),
                reverse(
                    'post',
                    kwargs={'username': self.user.username, 'post_id': 1}
                )
            ]
            time.sleep(20)
            for url in urls:
                resp = self.client.get(url, follow=True)
                self.assertContains(resp, '<img')

        img = tempfile.NamedTemporaryFile()
        response = self.auth_client.post(
            reverse(
                'post_edit',
                kwargs={'username': self.user.username, 'post_id': 1}
            ),
            {'text': self.post_text, 'group': self.group.id, 'image': img},
            follow=True
        )
        form = response.context['form']
        errors = form.errors['image']
        print(errors)
        # Проверяем что пост с некартинкой вызывает ошибку
        self.assertFormError(
            response=response,
            form='form',
            field='image',
            errors=errors,
            msg_prefix=''
        )
        img.close()

    def test_cache(self):
        # Запрашиваем страницу и кешируем
        self.client.get(reverse('index'))

        # Создаем пост
        Post.objects.create(
            author=self.user,
            group=self.group,
            text='cache test'
        )
        # Проверяем, что post не появился
        response = self.client.get(reverse('index'))
        self.assertNotIn('post', response.context.keys())
        # Проверяем, что post появился после 20 сек
        time.sleep(20)
        response = self.client.get(reverse('index'))
        self.assertIn('post', response.context.keys())

    def test_subscribe(self):
        subscr_before = self.user.follower.count()
        self.auth_client.get(
            reverse("profile_follow", args=[self.author_user])
        )
        subscr_after = self.user.follower.count()
        self.assertEquals(subscr_before, 0)
        self.assertEquals(subscr_after, 1)

    def test_unsubscribe(self):
        Follow.objects.create(
            author=self.author_user,
            user=self.user
        )
        subscr_before = self.user.follower.count()
        self.auth_client.get(
            reverse("profile_unfollow", args=[self.author_user])
        )
        subscr_after = self.user.follower.count()
        self.assertEquals(subscr_before, 1)
        self.assertEquals(subscr_after, 0)

    def test_subscription_list(self):
        author_text = 'Привет друзья подписчики! Ставим лайки'
        Follow.objects.create(
            author=self.author_user,
            user=self.user
        )
        Post.objects.create(
            author=self.author_user,
            group=self.group,
            text=author_text
        )
        # Проверяем, что пост автора
        # появляется в ленте у подписчика
        self.is_in_page(
            reverse('follow_index'),
            self.author_user,
            self.group,
            author_text
        )

        # Пост не отображается у неподписчиков
        self.auth_client.force_login(self.user2)
        response = self.auth_client.get(reverse('follow_index'), follow=True)
        posts_num = len(response.context['page'].object_list)
        self.assertEquals(posts_num, 0)

    def test_comment(self):
        post = Post.objects.create(
            author=self.user,
            group=self.group,
            text=self.post_text
        )

        # Не авторизованный пользователь
        # не может комментировать
        self.client.post(
            reverse(
                'add_comment',
                kwargs={'username': self.user.username, 'post_id': 1}
            ),
            {'author': self.user, 'post': post, 'text': 'comment text'},
            follow=True
        )
        comment_num = Comment.objects.count()
        self.assertEquals(comment_num, 0)

        # Авторизованный пользователь
        # может комментировать
        self.auth_client.post(
            reverse(
                'add_comment',
                kwargs={'username': self.user.username, 'post_id': 1}
            ),
            {'author': self.user, 'post': post, 'text': 'comment text'},
            follow=True
        )
        comment_num = Comment.objects.count()
        self.assertEquals(comment_num, 1)
