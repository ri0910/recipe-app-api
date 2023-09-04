from decimal import Decimal
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.test import TestCase

from rest_framework import status
from rest_framework.test import APIClient

import tempfile
from PIL import Image
import os

from core.models import (
    Recipe,
    Tag,
    Ingredient
)

from recipe.serializers import (
    RecipeSerializer,
    RecipeDetailsSerializer
)

RECIPE_URL = reverse('recipe:recipe-list')


def detail_url(recipe_id):
    return reverse('recipe:recipe-detail', args=[recipe_id])


def image_upload_url(recipe_id):
    return reverse('recipe:recipe-upload-image', args=[recipe_id])


def create_recipe(user, **params):
    defaults = {
        'title': 'recipe for test',
        'time_minutes': 22,
        'price': Decimal('5.24'),
        'description': 'description for test'
    }

    defaults.update(params)

    recipe = Recipe.objects.create(user=user, **defaults)
    return recipe


def create_user(**params):
    return get_user_model().objects.create(**params)


class PublicRecipeAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_unauthenticated(self):
        res = self.client.get(RECIPE_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateRecipesTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = create_user(email='test@example.com', password='test@123')
        self.client.force_authenticate(self.user)

    def test_recipe_list(self):
        create_recipe(user=self.user)
        create_recipe(user=self.user)

        res = self.client.get(RECIPE_URL)
        recipes = Recipe.objects.all().order_by('-id')
        serializers = RecipeSerializer(recipes, many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializers.data)

    def test_recipe_for_limited_user(self):
        other_user = create_user(
            email='other@example.com', password='other@123')
        create_recipe(user=other_user)
        create_recipe(user=self.user)

        res = self.client.get(RECIPE_URL)
        recipes = Recipe.objects.filter(user=self.user)
        serializers = RecipeSerializer(recipes, many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializers.data)

    def test_recipe_detail(self):
        recipe = create_recipe(user=self.user)
        url = detail_url(recipe.id)
        res = self.client.get(url)
        serializer = RecipeDetailsSerializer(recipe)
        self.assertEqual(res.data, serializer.data)

    def test_create_recipe(self):
        payload = {
            'title': 'sample title',
            'time_minutes': 22,
            'price': Decimal('5')
        }
        res = self.client.post(RECIPE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipe = Recipe.objects.get(id=res.data['id'])
        for k, v in payload.items():
            self.assertEqual(getattr(recipe, k), v)

        self.assertEqual(recipe.user, self.user)

    def test_partial_update(self):
        original_link = "https://example.com/recipe.pdf"
        recipe = create_recipe(
            user=self.user,
            title='some recipe title',
            link=original_link
        )

        payload = {'title': 'new recipe title'}
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        recipe.refresh_from_db()
        self.assertEqual(recipe.title, payload['title'])
        self.assertEqual(recipe.link, original_link)
        self.assertEqual(recipe.user, self.user)

    def test_full_update(self):
        recipe = create_recipe(
            user=self.user,
            title='Sample test title',
            link='http://example.com/recipe.pdf',
            description='Sample test description'
        )

        url = detail_url(recipe.id)
        payload = {
            'title': 'new recipe title',
            'link': 'http://example.com/newrecipe.pdf',
            'description': 'Sample test new description',
            'time_minutes': 45,
            'price': Decimal('9.8')
        }

        res = self.client.put(url, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        recipe.refresh_from_db()
        for k, v in payload.items():
            self.assertEqual(getattr(recipe, k), v)
        self.assertEqual(recipe.user, self.user)

    def test_update_user_returns(self):
        new_user = create_user(
            email="newuser@example.com", password="passwordnew")
        recipe = create_recipe(user=self.user)

        payload = {'user': new_user.id}
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        recipe.refresh_from_db()
        self.assertEqual(recipe.user, self.user)

    def test_delete_recipe(self):
        recipe = create_recipe(user=self.user)
        url = detail_url(recipe.id)

        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Recipe.objects.filter(id=recipe.id).exists())

    def test_delete_recipe_other_users_recipe_errors(self):
        other_user = create_user(
            email='other@example.com', password='other@123')
        recipe = create_recipe(user=other_user)

        url = detail_url(recipe.id)

        res = self.client.delete(url)
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(Recipe.objects.filter(id=recipe.id).exists())

    def test_create_recipe_with_new_tags(self):
        payload = {
            'title': 'Thai food',
            'time_minutes': 34,
            'price': Decimal('7.8'),
            'description': 'New Thai food',
            'tags': [
                {'name': 'Thai'},
                {'name': 'Night'}
            ]
        }
        res = self.client.post(RECIPE_URL, payload,
                               format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipes = Recipe.objects.filter(user=self.user)
        self.assertEqual(recipes.count(), 1)
        recipe = recipes[0]
        self.assertEqual(recipe.tags.count(), 2)
        for tag in payload['tags']:
            exist = recipe.tags.filter(
                name=tag['name'],
                user=self.user
            ).exists()
            self.assertTrue(exist)

    def test_create_recipe_with_existing_tags(self):
        tag_indian = Tag.objects.create(user=self.user, name='Indian')
        payload = {
            'title': 'Thai food',
            'time_minutes': 34,
            'price': Decimal('7.8'),
            'description': 'New Thai food',
            'tags': [
                {'name': 'Thai'},
                {'name': 'Indian'}
            ]
        }
        res = self.client.post(RECIPE_URL, payload,
                               format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipes = Recipe.objects.filter(user=self.user)
        self.assertEqual(recipes.count(), 1)
        recipe = recipes[0]
        self.assertEqual(recipe.tags.count(), 2)
        self.assertIn(tag_indian, recipe.tags.all())
        for tag in payload['tags']:
            exist = recipe.tags.filter(
                name=tag['name'],
                user=self.user
            ).exists()
            self.assertTrue(exist)

    def test_create_tag_on_update(self):
        recipe = create_recipe(user=self.user)
        url = detail_url(recipe.id)
        payload = {'tags': [{'name': 'Lunch'}]}
        res = self.client.patch(url, payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        new_tag = Tag.objects.get(user=self.user)
        self.assertIn(new_tag, Tag.objects.all())

    def test_update_recipe_tag(self):
        tag_breakfast = Tag.objects.create(user=self.user, name='Breakfast')
        recipe = create_recipe(user=self.user)
        recipe.tags.add(tag_breakfast)
        new_tag = Tag.objects.create(user=self.user, name='Lunch')
        payload = {'tags': [{'name': 'Lunch'}]}
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn(new_tag, recipe.tags.all())
        self.assertNotIn(tag_breakfast, recipe.tags.all())

    def test_clear_recipe_tags(self):
        """Test clearing a recipes tags."""
        tag = Tag.objects.create(user=self.user, name='Dessert')
        recipe = create_recipe(user=self.user)
        recipe.tags.add(tag)

        payload = {'tags': []}
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(recipe.tags.count(), 0)

    def test_create_recipe_with_new_ingredient(self):
        payload = {
            'title': 'CauliFlower Tacos',
            'time_minutes': 30,
            'price': Decimal('12.0'),
            'ingredients': [
                {'name': 'CauliFlower'},
                {'name': 'Sault'}
            ]
        }
        res = self.client.post(RECIPE_URL, payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipes = Recipe.objects.all()
        self.assertEqual(recipes.count(), 1)
        recipe = recipes[0]
        ingredients = payload['ingredients']
        self.assertEqual(recipe.ingredients.count(), 2)
        for ingredient in ingredients:
            exist = recipe.ingredients.filter(
                user=self.user,
                name=ingredient['name']
            ).exists()

        self.assertTrue(exist)

    def test_create_recipe_with_existing_tag(self):
        new_ingredient = Ingredient.objects.create(
            user=self.user, name='Water')
        payload = {
            'title': 'CauliFlower Tacos',
            'time_minutes': 30,
            'price': Decimal('12.0'),
            'ingredients': [
                {'name': 'CauliFlower'},
                {'name': 'Water'}
            ]
        }
        res = self.client.post(RECIPE_URL, payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipes = Recipe.objects.all()
        self.assertEqual(recipes.count(), 1)
        recipe = recipes[0]
        ingredients = payload['ingredients']
        self.assertEqual(recipe.ingredients.count(), 2)
        self.assertIn(new_ingredient, recipe.ingredients.all())
        for ingredient in ingredients:
            exist = recipe.ingredients.filter(
                user=self.user,
                name=ingredient['name']
            ).exists()

        self.assertTrue(exist)

    def test_create_ingredients_on_update(self):
        recipe = create_recipe(user=self.user)
        url = detail_url(recipe.id)
        ingredient = {
            'ingredients': [
                {'name': 'sault'}
            ]
        }
        res = self.client.patch(url, ingredient, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        new_ingredient = Ingredient.objects.get(user=self.user)
        self.assertIn(new_ingredient, Ingredient.objects.all())

    def test_update_recipe_ingredient(self):
        first_ingredient = Ingredient.objects.create(
            user=self.user, name="Sault")
        recipe = create_recipe(user=self.user)
        recipe.ingredients.add(first_ingredient)
        second_ingredient = Ingredient.objects.create(
            user=self.user, name="Sugar")
        payload = {
            'ingredients': [
                {'name': 'Sugar'}
            ]
        }
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn(second_ingredient, recipe.ingredients.all())
        self.assertNotIn(first_ingredient, recipe.ingredients.all())

    def test_clear_recipe_ingredients(self):
        """Test clearing a recipes ingredients."""
        ingredient = Ingredient.objects.create(user=self.user, name='Garlic')
        recipe = create_recipe(user=self.user)
        recipe.ingredients.add(ingredient)

        payload = {'ingredients': []}
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(recipe.ingredients.count(), 0)

    def test_filter_by_tags(self):
        r1 = create_recipe(user=self.user, title='Chicken curry')
        r2 = create_recipe(user=self.user, title='Vegetable curry')
        t1 = Tag.objects.create(user=self.user, name='Non-veg')
        t2 = Tag.objects.create(user=self.user, name='Veg')
        r1.tags.add(t1)
        r2.tags.add(t2)
        r3 = create_recipe(user=self.user, title='Fish curry')

        params = {'tags': f'{t1.id}, {t2.id}'}

        res = self.client.get(RECIPE_URL, params)

        s1 = RecipeSerializer(r1)
        s2 = RecipeSerializer(r2)
        s3 = RecipeSerializer(r3)

        self.assertIn(s1.data, res.data)
        self.assertIn(s2.data, res.data)
        self.assertNotIn(s3.data, res.data)

    def test_filter_by_ingredients(self):
        r1 = create_recipe(user=self.user, title='Chicken curry')
        r2 = create_recipe(user=self.user, title='Vegetable curry')
        i1 = Ingredient.objects.create(user=self.user, name='Sault')
        i2 = Ingredient.objects.create(user=self.user, name='Sweet')
        r1.ingredients.add(i1)
        r2.ingredients.add(i2)
        r3 = create_recipe(user=self.user, title='Fish curry')

        params = {'ingredients': f'{i1.id}, {i2.id}'}

        res = self.client.get(RECIPE_URL, params)

        s1 = RecipeSerializer(r1)
        s2 = RecipeSerializer(r2)
        s3 = RecipeSerializer(r3)

        self.assertIn(s1.data, res.data)
        self.assertIn(s2.data, res.data)
        self.assertNotIn(s3.data, res.data)


class ImageUploadTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = create_user(email='test@example.com', password='test@123')
        self.client.force_authenticate(self.user)
        self.recipe = create_recipe(user=self.user)

    def tearDown(self):
        return self.recipe.image.delete()

    def test_image_upload(self):
        url = image_upload_url(self.recipe.id)
        with tempfile.NamedTemporaryFile(suffix='.jpg') as image_file:
            img = Image.new('RGB', (10, 10))
            img.save(image_file, format='JPEG')
            image_file.seek(0)
            payload = {'image': image_file}
            res = self.client.post(url, payload, format='multipart')

        self.recipe.refresh_from_db()
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn('image', res.data)
        self.assertTrue(os.path.exists(self.recipe.image.path))
