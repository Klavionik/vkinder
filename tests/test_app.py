# FIXME: The test is obsolete
import json
import os
import unittest
from unittest.mock import patch, MagicMock

from vkinder.globals import root, data

from vkinder import app as vkinder
from vkinder.db import db_session, Base
from vkinder.types import User

output_amount = 10
fixtures_path = os.path.join(root, 'tests', 'fixtures')
db_path = os.path.join(fixtures_path, "test.db")
mock_print = MagicMock()

with open(f"{os.path.join(fixtures_path, 'user.json')}") as f:
    user = json.load(f)
with open(f"{os.path.join(fixtures_path, 'groups.json')}", encoding='utf8') as f:
    groups = json.load(f)
with open(f"{os.path.join(fixtures_path, 'matches.json')}", encoding='utf8') as f:
    matches = json.load(f)


@patch('builtins.print', mock_print)
class TestApp(unittest.TestCase):

    def setUp(self) -> None:
        self.app = vkinder.App('test_id',
                               'test_token',
                               output_amount=output_amount,
                               refresh=False,
                               db=db_path)

    def tearDown(self) -> None:
        Base.metadata.drop_all(self.app.db.db)

    @classmethod
    def tearDownClass(cls) -> None:
        os.remove(db_path)
        os.remove(os.path.join(data, f'{user[0]["id"]}_matches.json'))

    @patch('vkinder.app.App._fetch_user_groups')
    @patch('vkinder.app.App._fetch_user')
    def test_new_user_from_api(self, mock_fetch_user, mock_fetch_user_groups):
        mock_fetch_user.return_value = (user[0]['id'], user[0])
        mock_fetch_user_groups.return_value = groups

        self.app.new_user(user[0]['id'])

        self.assertIsNotNone(self.app.current_user,
                             'User fetched from API and assigned to the class attribute')
        self.assertIsInstance(self.app.current_user, User,
                              'App assigned a :class:`User` instance')
        self.assertEqual(self.app.current_user.uid, user[0]['id'],
                         'A :class:`User` instance uid matches test user id')

    @patch('vkinder.app.App._fetch_user')
    def test_new_user_from_database(self, mock_fetch_user):
        mock_fetch_user.return_value = (user[0]['id'], None)
        with db_session(self.app.db.factory) as session:
            self.app.db.add_user(User.from_api(user[0], groups), session)

        self.app.new_user(user[0]['id'])

        self.assertIsNotNone(self.app.current_user,
                             'User loaded and assigned to the class attribute')
        self.assertIsInstance(self.app.current_user, User,
                              'App assigned a :class:`User` instance')
        self.assertEqual(self.app.current_user.uid, user[0]['id'],
                         'A :class:`User` instance uid matches test user id')

    @patch('vkinder.app.App._fetch_user_groups')
    @patch('vkinder.app.App._fetch_user')
    @patch('vkinder.app.App._prepare_matches')
    def test_spawn_matches(self, mock_prepare_matches, mock_fetch_user, mock_fetch_user_groups):
        matches_length = len(matches['matches_info'])
        mock_prepare_matches.return_value = (matches['matches_info'],
                                             matches['matches_groups'],
                                             matches['matches_photos'])
        mock_fetch_user.return_value = (user[0]['id'], user[0])
        mock_fetch_user_groups.return_value = groups

        self.assertFalse(self.app.spawn_matches(),
                         'Returns False if no user set')
        self.app.new_user(user[0]['id'])
        self.assertEqual(self.app.spawn_matches(), matches_length,
                         'Returns number of found matches')
        self.assertEqual(matches_length, len(self.app.matches),
                         'All found matches assigned to the class attribute')

    @patch('vkinder.app.App._fetch_user_groups')
    @patch('vkinder.app.App._fetch_user')
    def test_list_users(self, mock_fetch_user, mock_fetch_user_groups):
        mock_fetch_user.return_value = (user[0]['id'], user[0])
        mock_fetch_user_groups.return_value = groups

        self.assertFalse(self.app.list_users(),
                         'Returns False if no users present in the db')
        self.app.new_user(user[0]['id'])
        self.assertEqual(len(self.app.list_users()), 1,
                         'Returns all users from the db')

    @patch('vkinder.app.App._fetch_user_groups')
    @patch('vkinder.app.App._fetch_user')
    @patch('vkinder.app.App._prepare_matches')
    def test_next_matches(self, mock_prepare_matches, mock_fetch_user, mock_fetch_user_groups):
        mock_prepare_matches.return_value = (matches['matches_info'],
                                             matches['matches_groups'],
                                             matches['matches_photos'])
        mock_fetch_user.return_value = (user[0]['id'], user[0])
        mock_fetch_user_groups.return_value = groups

        self.assertFalse(self.app.next_matches(user[0]['id']),
                         'Returns False if the user is not present in the db')
        self.app.new_user(user[0]['id'])
        self.app.spawn_matches()
        self.assertEqual(self.app.next_matches(user[0]['id']), 10,
                         'First call should return 10 records')
        self.assertEqual(self.app.next_matches(user[0]['id']), 10,
                         'Second call should return 10 records')
        self.assertEqual(self.app.next_matches(user[0]['id']), 1,
                         'Third call should return 1 record')
        self.assertEqual(self.app.next_matches(user[0]['id']), 0,
                         'Fouth call should return 0 record')


if __name__ == '__main__':
    unittest.main()
