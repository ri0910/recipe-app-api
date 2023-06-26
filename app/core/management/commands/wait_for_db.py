<<<<<<< HEAD
'''
Django command to wait for the database to be available
'''

from psycopg2 import OperationalError as Psycopg2Error
=======
from psycopg2 import OperationalError as Psycopg2OpError

>>>>>>> a02bb0d (Configured docker compose and checks for wait_for_db)
from django.db.utils import OperationalError
from django.core.management.base import BaseCommand
import time

<<<<<<< HEAD
class Command(BaseCommand):
    '''Django command to wait for database'''

    def handle(self, *args, **options):
        self.stdout.write('Waiting for database to be available....')
        db_up = False
        while db_up is False:
            try:
                self.check(databases = ['default'])
                db_up = True
            except (Psycopg2Error, OperationalError):
                self.stdout.write('Database unavailable, waiting for 1 second...')
                time.sleep(1)


        self.stdout.write(self.style.SUCCESS('Database available...'))
=======

class Command(BaseCommand):

    def handle(self, *args, **options):
        """ Entrypoint for command """
        self.stdout.write('Waiting for database...')
        db_up = False
        while db_up is False:
            try:
                self.check(databases=['default'])
                db_up = True
            except(Psycopg2OpError, OperationalError):
                self.stdout.write('Database unavailable, waiting for 1 sec!')
                time.sleep(1)

        self.stdout.write(self.style.SUCCESS('Database available!'))
>>>>>>> a02bb0d (Configured docker compose and checks for wait_for_db)
