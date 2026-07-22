from django.core.management.base import BaseCommand
from corpus.models import Style, Genre

# docker compose exec backend python manage.py setup_defaults

class Command(BaseCommand):
    help = 'Fills the database with default styles and genres for the corpus'

    def handle(self, *args, **kwargs):
        default_data = {
            'Розмовний': [
                'Усне джерело'
            ],
            'Науковий': [
                'Дисертація', 'Монографія', 'Стаття', 'Підручник',
                'Лекція', 'Відгук', 'Анотація'
            ],
            'Офіційно-діловий': [
                'Закон', 'Кодекс', 'Статут', 'Наказ', 'Указ', 'Оголошення',
                'Доручення', 'Розписка', 'Протокол', 'Акт', 'Інструкція', 'Лист'
            ],
            'Публіцистичний': [
                'Виступ', 'Нарис', 'Публіцистична стаття', 'Памфлет',
                'Фейлетон', 'Дискусія'
            ],
            'Художній': [
                'Трагедія', 'Комедія', 'Драма', 'Водевіль', 'Роман',
                'Повість', 'Поема', 'Вірш', 'Байка', 'Поезія'
            ],
            'Інтернет дискус': [
                'Блог', 'Допис'
            ]
        }

        self.stdout.write("Starting to populate the database...")

        styles_created = 0
        genres_created = 0

        for style_name, genres_list in default_data.items():
            style_obj, created = Style.objects.get_or_create(name=style_name)
            if created:
                styles_created += 1

            for genre_name in genres_list:
                _, g_created = Genre.objects.get_or_create(
                    name=genre_name,
                    style=style_obj
                )
                if g_created:
                    genres_created += 1

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully completed! Added new styles: {styles_created}, genres: {genres_created}'
            )
        )