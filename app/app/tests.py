from django.test import SimpleTestCase

from app import calc

<<<<<<< HEAD
class CalcTestCase(SimpleTestCase):
    def test_add_numbers(self):
        res = calc.add(5,6)
        self.assertEqual(res,11)
=======

class CalcTestCase(SimpleTestCase):
    def test_add_numbers(self):
        res = calc.add(5, 6)
        self.assertEqual(res, 11)
>>>>>>> a02bb0d (Configured docker compose and checks for wait_for_db)
