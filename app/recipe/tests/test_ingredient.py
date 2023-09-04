from django.contrib.auth import get_user_model
from django.test import TestCase

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from core.models import (
    Ingredient,
    Recipe
)
from decimal import Decimal
from recipe.serializers import IngredientSerializer


def create_user(email="example@example.com", password="example@123"):
    return get_user_model().objects.create_user(email=email, password=password)


INGREDIENT_URL = reverse('recipe:ingredient-list')


def detail_url(ingredient_id):
    return reverse('recipe:ingredient-detail', args=[ingredient_id])


class PublicAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_get_ingredient_list(self):
        res = self.client.get(INGREDIENT_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateAPITest(TestCase):
    def setUp(self):
        self.user = create_user()
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_get_ingrediant_list(self):
        Ingredient.objects.create(user=self.user, name="Ingredient 1")
        Ingredient.objects.create(user=self.user, name="Ingredient 2")
        res = self.client.get(INGREDIENT_URL)
        ingredients = Ingredient.objects.all().order_by('-name')
        serializer = IngredientSerializer(ingredients, many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_ingrediant_for_limited_user(self):
        user2 = create_user(email="user2@example.com")
        Ingredient.objects.create(user=user2, name="salt")
        new_ingrediant = Ingredient.objects.create(
            user=self.user, name="mirchi")
        res = self.client.get(INGREDIENT_URL)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]['id'], new_ingrediant.id)
        self.assertEqual(res.data[0]['name'], new_ingrediant.name)

    def test_update_ingrediant(self):
        ingrediant = Ingredient.objects.create(
            user=self.user, name="Old ingrediant")
        payload = {'name': 'New Ingrediant'}
        url = detail_url(ingrediant.id)
        res = self.client.patch(url, payload)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        ingrediant.refresh_from_db()
        self.assertEqual(ingrediant.name, payload['name'])

    def test_delete_ingrediant(self):
        ingredient = Ingredient.objects.create(user=self.user, name="Lettuce")
        url = detail_url(ingredient.id)
        res = self.client.delete(url)
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        ingredients = Ingredient.objects.all()
        self.assertFalse(ingredients.exists())

    def test_filter_ingredients_assigned_to_recipes(self):
        """Test listing ingedients to those assigned to recipes."""
        in1 = Ingredient.objects.create(user=self.user, name='Apples')
        in2 = Ingredient.objects.create(user=self.user, name='Turkey')
        recipe = Recipe.objects.create(
            title='Apple Crumble',
            time_minutes=5,
            price=Decimal('4.50'),
            user=self.user,
        )
        recipe.ingredients.add(in1)

        res = self.client.get(INGREDIENT_URL, {'assigned_only': 1})

        s1 = IngredientSerializer(in1)
        s2 = IngredientSerializer(in2)
        self.assertIn(s1.data, res.data)
        self.assertNotIn(s2.data, res.data)

    def test_filtered_ingredients_unique(self):
        """Test filtered ingredients returns a unique list."""
        ing = Ingredient.objects.create(user=self.user, name='Eggs')
        Ingredient.objects.create(user=self.user, name='Lentils')
        recipe1 = Recipe.objects.create(
            title='Eggs Benedict',
            time_minutes=60,
            price=Decimal('7.00'),
            user=self.user,
        )
        recipe2 = Recipe.objects.create(
            title='Herb Eggs',
            time_minutes=20,
            price=Decimal('4.00'),
            user=self.user,
        )
        recipe1.ingredients.add(ing)
        recipe2.ingredients.add(ing)

        res = self.client.get(INGREDIENT_URL, {'assigned_only': 1})

        self.assertEqual(len(res.data), 1)
