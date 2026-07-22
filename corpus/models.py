from django.db import models
from django.conf import settings
from django.contrib.postgres.fields import ArrayField

from smart_selects.db_fields import ChainedManyToManyField


class CorpusUserAccess(models.Model):
    class AccessLevel(models.TextChoices):
        VIEWER = 'V', 'Перегляд'
        EDITOR = 'E', 'Редагування'
        
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    corpus = models.ForeignKey('Corpus', on_delete=models.CASCADE)
    access_level = models.CharField(max_length=30, choices=AccessLevel.choices, default=AccessLevel.VIEWER)

    class Meta:
        unique_together = ('user', 'corpus')
    
    def __str__(self):
        return f"{self.user} -> {self.corpus.name} ({self.get_access_level_display()})"


class Corpus(models.Model):
    class CorpusType(models.TextChoices):
        GENERAL = 'G', 'Загальний'
        EDUCATIONAL = 'E', 'Навчальний'
        SPECIALIZED = 'S', 'Спеціалізований'

    class CorpusLanguage(models.TextChoices):
        UKRAINIAN = 'UK', 'Українська'

    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=200)
    description = models.TextField(null=True, blank=True)
    type = models.CharField(max_length=50, choices=CorpusType.choices, default=CorpusType.GENERAL) 
    language = models.CharField(max_length=32, choices=CorpusLanguage.choices, default=CorpusLanguage.UKRAINIAN)  
    update_time = models.DateTimeField(auto_now_add=True)

    creator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='created_corpuses')
    users = models.ManyToManyField(settings.AUTH_USER_MODEL, through=CorpusUserAccess, blank=True, related_name='invited_corpuses')

    def __str__(self): return self.name


class UserSubcorpus(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=200)
    creator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=False, blank=False)
    corpus = models.ForeignKey(Corpus, on_delete=models.CASCADE)
    
    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['creator', 'corpus'],
                name='unique_user_subcorpus_name'
            )
        ]
    def __str__(self): return f"{self.name} ({self.creator})"


class Text(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=300)
    description = models.TextField(null=True, blank=True)
    corpus = models.ForeignKey(Corpus, on_delete=models.CASCADE, null=True, blank=True)
    user_subcorpus = models.ForeignKey(UserSubcorpus, on_delete=models.CASCADE, null=True, blank=True)
    creator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=(
                    models.Q(corpus__isnull=False, user_subcorpus__isnull=True) |
                    models.Q(corpus__isnull=True, user_subcorpus__isnull=False)
                ),
                name='text_belongs_to_exactly_one_parent'
            )
        ]
    def __str__(self): return self.name


class FilteredSubcorpus(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=200)
    texts = models.ManyToManyField(Text, blank=True)
    corpus = models.ForeignKey(Corpus, on_delete=models.CASCADE, null=False, blank=False)
    creator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=False, blank=False)
    creation_time = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['name', 'corpus', 'creator'],
                name='unique_filtered_subcorpus_name'
            )
        ]
    def __str__(self): return f"{self.corpus.name} - {self.name}"


class Style(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class Genre(models.Model):
    name = models.CharField(max_length=100)
    style = models.ForeignKey(Style, on_delete=models.CASCADE, related_name='genres')

    class Meta:
        unique_together = ('name', 'style')
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.style.name})"


class TextMetadata(models.Model):
    class TextOrigin(models.TextChoices):
        ORIGINAL = 'O', 'Оригінал'
        TRANSLATION = 'T', 'Переклад'
        UNKNOWN = 'U', 'Невідомо'
        
    class Gender(models.TextChoices):
        MALE = 'M', 'Чоловіча'
        FEMALE = 'F', 'Жіноча'
        OTHER = 'O', 'Інше'
        UNKNOWN = 'U', 'Невідомо'

    text = models.OneToOneField(Text, related_name="metadata", on_delete=models.CASCADE, primary_key=True)
    style = models.ForeignKey(Style, on_delete=models.SET_NULL, null=True, blank=True)
    genres = ChainedManyToManyField(Genre, chained_field="style", chained_model_field="style", horizontal=True, blank=True)
    year_of_creation = models.PositiveSmallIntegerField(null=True, blank=True)
    years_of_publication = ArrayField(models.IntegerField(), null=True, blank=True)
    author = models.CharField(max_length=255, null=True, blank=True)
    authors_gender = models.CharField(max_length=1, choices=Gender.choices, null=True, blank=True)
    source = models.CharField(max_length=500, null=True, blank=True)
    text_origin = models.CharField(max_length=1, choices=TextOrigin.choices, null=True, blank=True)

    def __str__(self): return f"Metadata for {self.text.name}"
