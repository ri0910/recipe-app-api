from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse


from rest_framework.test import APIClient
from rest_framework import status


CREATE_USER_MODEL_URL = reverse('user:create')
TOKEN_URL = reverse('user:token')
ME_URL = reverse('user:me')


def create_user(**params):
    return get_user_model().objects.create_user(**params)


class PublicUserAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_create_user(self):
        payload = {
            'email': 'test@example.com',
            'password': 'test123',
            'name': 'test'
        }

        res = self.client.post(CREATE_USER_MODEL_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        user = get_user_model().objects.get(email=payload['email'])
        self.assertTrue(user.check_password(payload['password']))

    def test_user_already_exists(self):
        payload = {
            'email': 'test@example.com',
            'password': 'test123',
            'name': 'test'
        }

        create_user(**payload)
        res = self.client.post(CREATE_USER_MODEL_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_password_too_small(self):
        payload = {
            'email': 'test@example.com',
            'password': 'pw',
            'name': 'test'
        }

        res = self.client.post(CREATE_USER_MODEL_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        user_exists = get_user_model().objects.filter(
            email=payload['email']
        ).exists()
        self.assertFalse(user_exists)

    def test_create_user_token(self):
        credentials = {
            'email': 'test@example.com',
            'password': 'test_user@123',
            'name': 'test name'
        }
        create_user(**credentials)
        payload = {
            'email': credentials['email'],
            'password': credentials['password'],
        }

        res = self.client.post(TOKEN_URL, payload)
        self.assertIn('token', res.data)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_create_token_bad_user_credentials(self):
        create_user(email='test@example.com', password='goodpass')
        payload = {
            'email': 'test@example.com',
            'password': 'badpass'
        }
        res = self.client.post(TOKEN_URL, payload)
        self.assertNotIn('token', res.data)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_token_blank_password(self):
        create_user(email='test@example.com', password='goodpass')
        payload = {
            'email': 'test@example.com',
            'password': ''
        }
        res = self.client.post(TOKEN_URL, payload)
        self.assertNotIn('token', res.data)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_retrieve_user_unauthenticated(self):
        res = self.client.get(ME_URL)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateUserApiTest(TestCase):
    def setUp(self):
        self.user = create_user(
            email='user@example.com',
            password='test@123',
            name='test name'
        )

        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_retrieve_profile_success(self):
        res = self.client.get(ME_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)

        self.assertEqual(res.data, {
            'name': self.user.name,
            'email': self.user.email
        })

    def test_post_me_not_allowed(self):
        res = self.client.post(ME_URL, {})

        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_update_profile(self):
        payload = {
            'name': 'updated name',
            'password': 'updatedpass123'
        }

        res = self.client.patch(ME_URL, payload)
        self.user.refresh_from_db()

        self.assertEqual(self.user.name, payload['name'])
        self.assertTrue(self.user.check_password(payload['password']))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
