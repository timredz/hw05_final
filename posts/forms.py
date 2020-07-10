from django.forms import ModelForm, Textarea
from .models import Post, Comment


class PostForm(ModelForm):
    class Meta:
        model = Post
        fields = ['group', 'text', 'image']
        labels = {
            'text': 'Текст',
            'group': 'Сообщество',
            'image': 'Заглавная картинка'
        }
        help_texts = {
            'text': 'Довольно скучных историй, только трэш',
        }

class CommentForm(ModelForm):
    class Meta:
        model = Comment
        fields = ['text']
        widgets = {'text': Textarea(attrs={'cols': 40, 'rows': 5})}
        labels = {
            'text': 'Текст комментария',
        }
