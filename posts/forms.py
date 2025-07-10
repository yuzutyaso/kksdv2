# posts/forms.py
from django import forms
from .models import Post
import bleach # HTMLタグ除去用
import unicodedata # Zalgo除去用

def remove_zalgo(text):
    normalized_text = unicodedata.normalize('NFD', text)
    cleaned_text = ''.join(
        char for char in normalized_text
        if not unicodedata.category(char).startswith('M')
    )
    return unicodedata.normalize('NFC', cleaned_text)

class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ['title', 'content']
        widgets = {
            'title': forms.TextInput(attrs={'maxlength': 100}),
            'content': forms.Textarea(attrs={'maxlength': 1000}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['title'].required = False # タイトルを必須ではないように

    def clean_title(self):
        title = self.cleaned_data.get('title') # .get() を使うことで、空の場合もNoneを返す
        if title:
            # タグ除去
            cleaned_title = bleach.clean(title, tags=[], attributes={})
            # Zalgo除去
            cleaned_title = remove_zalgo(cleaned_title)
            return cleaned_title
        return title # タイトルが空の場合はそのまま返す

    def clean_content(self):
        content = self.cleaned_data['content'] # contentは必須なのでget()は不要
        # タグ除去
        cleaned_content = bleach.clean(content, tags=[], attributes={})
        # Zalgo除去
        cleaned_content = remove_zalgo(cleaned_content)
        return cleaned_content
