from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth import get_user_model
from rest_framework.validators import UniqueValidator
from corpus.models import Corpus, UserSubcorpus


User = get_user_model()


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Serializer for logging in
    """
    identifier = serializers.CharField()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields.pop(self.username_field, None)

    def validate(self, attrs):
        identifier = self.initial_data.get('identifier')
        password = self.initial_data.get('password')

        user = User.objects.filter(email=identifier).first()
        if not user and identifier:
            user = User.objects.filter(phone_number=identifier).first()
            if not user:
                import re
                cleaned = re.sub(r'[\s\(\)\-]', '', identifier)
                if cleaned.startswith('0') and len(cleaned) == 10:
                    cleaned = '+38' + cleaned
                elif cleaned.startswith('380') and len(cleaned) == 12:
                    cleaned = '+' + cleaned
                user = User.objects.filter(phone_number=cleaned).first()

        # Check password
        if user and user.check_password(password):
            refresh = self.get_token(user)
            return {
                'access': str(refresh.access_token),
                'refresh': str(refresh),
                'user_id': user.id,
                'user_full_name': user.full_name,
                'user_phone_number': user.phone_number,
                'user_email': user.email,
                'user_role': user.role,
            }
            
        raise serializers.ValidationError({"detail": "Неправильний логін чи пароль"})


class UserRegistrationSerializer(serializers.ModelSerializer):
    """
    Serializer for registration
    """
    password = serializers.CharField(
        write_only=True, 
        min_length=8, 
        style={'input_type': 'password'},
        error_messages={
            'min_length': 'Пароль повинен містити не менше 8 символів.',
            'blank': 'Пароль не може бути порожнім.',
            'required': 'Пароль є обов\'язковим.'
        }
    )

    email = serializers.EmailField(
        required=True,
        validators=[
            UniqueValidator(
                queryset=User.objects.all(),
                message='Користувач з такою електронною поштою вже зареєстрований.'
            )
        ],
        error_messages={
            'invalid': 'Введіть коректну електронну адресу.',
            'blank': 'Це поле не може бути порожнім.',
            'required': 'Це поле є обов\'язковим.'
        }
    )
    phone_number = serializers.CharField(
        required=True,
        max_length=20,
        validators=[
            UniqueValidator(
                queryset=User.objects.all(),
                message='Користувач з таким номером телефону вже зареєстрований.'
            )
        ],
        error_messages={
            'max_length': 'Номер телефону занадто довгий. Максимальна довжина - 20 символів.'
        }
    )

    class Meta:
        model = User
        fields = ('email', 'full_name', 'phone_number', 'password')

    def validate_phone_number(self, value):
        import re
        cleaned = re.sub(r'[\s\(\)\-]', '', value)

        if cleaned.startswith('0') and len(cleaned) == 10:
            cleaned = '+38' + cleaned
        elif cleaned.startswith('380') and len(cleaned) == 12:
            cleaned = '+' + cleaned

        if not re.match(r'^\+\d{10,14}$', cleaned):
            raise serializers.ValidationError(
                "Некоректний номер телефону. Використовуйте формат +380XXXXXXXXX або 0XXXXXXXXX (12 цифр з кодом країни)."
            )

        return cleaned

    def validate_password(self, value):
        if not any(char.isdigit() for char in value):
            raise serializers.ValidationError("Пароль повинен містити принаймні одну цифру.")
        if not any(char.isalpha() for char in value):
            raise serializers.ValidationError("Пароль повинен містити принаймні одну літеру.")
        return value

    def create(self, validated_data):
        user = User.objects.create_user(
            email=validated_data['email'],
            password=validated_data['password'],
            full_name=validated_data.get('full_name', ''),
            phone_number=validated_data.get('phone_number', '')
        )
        return user

class UserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['full_name']

    def validate_full_name(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Ім'я не може бути порожнім.")
        return value.strip()

class AdminUserListSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'email', 'full_name', 'phone_number', 'role', 'date_joined')
        read_only_fields = fields


class AdminUserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True,
        min_length=8,
        error_messages={
            'min_length': 'Пароль повинен містити не менше 8 символів.',
        }
    )
    role = serializers.ChoiceField(choices=User.Role.choices, default=User.Role.USER)

    class Meta:
        model = User
        fields = ('email', 'full_name', 'phone_number', 'password', 'role')

    def validate_password(self, value):
        if not any(char.isdigit() for char in value):
            raise serializers.ValidationError("Пароль повинен містити принаймні одну цифру.")
        if not any(char.isalpha() for char in value):
            raise serializers.ValidationError("Пароль повинен містити принаймні одну літеру.")
        return value

    def create(self, validated_data):
        role = validated_data.pop('role', User.Role.USER)
        user = User.objects.create_user(
            email=validated_data['email'],
            password=validated_data['password'],
            full_name=validated_data.get('full_name', ''),
            phone_number=validated_data.get('phone_number', ''),
            role=role,
        )
        return user


class AdminUserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('role',)

    def validate_role(self, value):
        if value not in [choice[0] for choice in User.Role.choices]:
            raise serializers.ValidationError("Невалідна роль.")
        return value


class AdminCorpusListSerializer(serializers.ModelSerializer):
    creator_name = serializers.SerializerMethodField()
    creator_email = serializers.SerializerMethodField()
    creator_role = serializers.SerializerMethodField()
    creator_id = serializers.SerializerMethodField()
    text_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Corpus
        fields = ('id', 'name', 'type', 'language', 'creator_name', 'creator_email', 'creator_role', 'creator_id', 'text_count', 'update_time')

    def get_creator_name(self, obj):
        return obj.creator.full_name if obj.creator else None

    def get_creator_email(self, obj):
        return obj.creator.email if obj.creator else None

    def get_creator_role(self, obj):
        return obj.creator.role if obj.creator else None

    def get_creator_id(self, obj):
        return obj.creator.id if obj.creator else None


class AdminSubcorpusListSerializer(serializers.ModelSerializer):
    creator_name = serializers.SerializerMethodField()
    creator_email = serializers.SerializerMethodField()
    creator_role = serializers.SerializerMethodField()
    creator_id = serializers.SerializerMethodField()

    class Meta:
        model = UserSubcorpus
        fields = ('id', 'name', 'creator_name', 'creator_email', 'creator_role', 'creator_id')

    def get_creator_name(self, obj):
        return obj.creator.full_name if obj.creator else None

    def get_creator_email(self, obj):
        return obj.creator.email if obj.creator else None

    def get_creator_role(self, obj):
        return obj.creator.role if obj.creator else None

    def get_creator_id(self, obj):
        return obj.creator.id if obj.creator else None