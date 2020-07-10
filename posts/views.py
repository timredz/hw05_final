from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import render, get_object_or_404, redirect, reverse
from .forms import PostForm, CommentForm
from .models import Post, Group, User, Comment, Follow


def index(request):
    post_list = Post.objects.all()
    paginator = Paginator(post_list, 10)
    page_number = request.GET.get('page')
    page = paginator.get_page(page_number)
    return render(
        request,
        'index.html',
        {'page': page, 'paginator': paginator}
    )


@login_required
def new_post(request):
    if request.method == 'POST':
        form = PostForm(request.POST)
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user
            post.save()
            return redirect('index')
        return render(request, 'posts/new.html', {'form': form})

    form = PostForm()
    return render(request, 'posts/new.html', {'form': form})


def group_posts(request, slug):
    group = get_object_or_404(Group, slug=slug)
    posts = group.posts.all()
    paginator = Paginator(posts, 3)
    page_number = request.GET.get('page')
    page = paginator.get_page(page_number)

    return render(
        request,
        "group.html",
        {"group": group, "page": page, 'paginator': paginator}
    )


def profile(request, username):
    user = get_object_or_404(User, username=username)
    userposts = user.posts.all()
    paginator = Paginator(userposts, 10)
    page_number = request.GET.get('page')
    page = paginator.get_page(page_number)
    following_num = Follow.objects.filter(user=user).count()
    follower_num = Follow.objects.filter(author=user).count()
    following = False
    if request.user.is_authenticated:
        if Follow.objects.filter(user=request.user, author=user).exists():
            following = True

    return render(
        request,
        'profile.html',
        {'userdata': user, 'page': page, 'paginator': paginator,
         'following': following, 'following_num': following_num,
         'follower_num': follower_num}
    )


def post_view(request, username, post_id):
    userpost = get_object_or_404(Post, id=post_id, author__username=username)
    userposts_count = userpost.author.posts.count()
    comments = userpost.comments.select_related('author')
    form = CommentForm()
    return render(
        request, 'post.html',
        {'userdata': userpost.author, 'post': userpost, 'form': form,
         'userposts_count': userposts_count, 'comments': comments}
    )


@login_required
def post_edit(request, username, post_id):
    post = get_object_or_404(Post, id=post_id, author__username=username)
    post_url = reverse('post', args=(post.author, post.id))

    if post.author != request.user:
        return redirect(post_url)

    form = PostForm(
        data=request.POST or None,
        files=request.FILES or None,
        instance=post
    )

    if form.is_valid():
        post.save()
        return redirect(post_url)

    return render(
        request,
        'posts/new.html',
        {'form': form, 'post': post, 'post_edit': True}
    )


def page_not_found(request, exception):
    return render(
        request,
        "misc/404.html",
        {"path": request.path},
        status=404
    )


def server_error(request):
    return render(request, "misc/500.html", status=500)


@login_required
def add_comment(request, username, post_id):
    post = get_object_or_404(Post, pk=post_id)
    if request.method == 'POST':
        form = CommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.author = request.user
            comment.post = post
            comment.save()
    return redirect(
        reverse("post", kwargs={'username': username, 'post_id': post_id})
    )


@login_required
def follow_index(request):
    post_list = Post.objects.select_related('author').filter(
        author__following__user=request.user
    )
    paginator = Paginator(post_list, 10)
    page_number = request.GET.get('page')
    page = paginator.get_page(page_number)
    return render(
        request,
        "follow.html",
        {'page': page, 'paginator': paginator}
    )


@login_required
def profile_follow(request, username):
    user_to_follow = get_object_or_404(User, username=username)
    if user_to_follow != request.user:
        if not Follow.objects.filter(
            user=request.user,
            author=user_to_follow
        ).exists():
            Follow.objects.create(
                author=user_to_follow,
                user=request.user
            )
    return redirect(reverse('profile', args=[user_to_follow.username]))


@login_required
def profile_unfollow(request, username):
    user_to_unfollow = get_object_or_404(User, username=username)
    Follow.objects.filter(author=user_to_unfollow, user=request.user).delete()
    return redirect(reverse('profile', args=[user_to_unfollow.username]))
