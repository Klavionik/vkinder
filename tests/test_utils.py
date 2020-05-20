import json
import os
import unittest

import vkinder.utils as utils
from vkinder import root

fixture_photos = os.path.join(root, 'tests', 'fixtures', 'utils_photos.json')


class UtilsTest(unittest.TestCase):
    def test_cleanup(self):
        text = '"here; were"!, too (^many )special /«chars»/|   '
        text1 = 'first\nsecond\n«third»'
        text2 = 'nothing special here'
        processed_text = ['here were', 'too many special chars']
        processed_text1 = ['first', 'second', 'third']
        processed_text2 = ['nothing special here']

        self.assertEqual(utils.cleanup(text), processed_text, 'No special characters')
        self.assertEqual(utils.cleanup(text1), processed_text1, 'Newline separate words')
        self.assertEqual(utils.cleanup(text2), processed_text2, 'This text should be string')

    def test_common(self):
        iterable1 = [1, 2, 3]
        iterable2 = [2, 3, 4]
        iterable3 = [5, 6, 7]

        self.assertEqual(utils.common(iterable1, iterable2), 2)
        self.assertEqual(utils.common(iterable2, iterable3), 0)

    def test_find_largest_photo(self):
        with open(fixture_photos) as f:
            photos = json.load(f)

        largest_w = photos['photo1']
        largest_m = photos['photo2']
        self.assertEqual(utils.find_largest_photo(largest_w),
                         'https://sun9-7.us...1/6/53_VwoACy4I.jpg',
                         'The largest photo is "w"')
        self.assertEqual(utils.find_largest_photo(largest_m),
                         'https://sun9-14.u...1/2/XF7JgWq3Chc.jpg',
                         'The largest photo is "m"')

    def test_flatten(self):
        nested_dict = {'key': {'key': 'value'}}
        flat_dict = {'key.key': 'value'}
        self.assertEqual(utils.flatten(nested_dict), flat_dict, 'Nested dict got flat')
        self.assertEqual(utils.flatten(flat_dict), flat_dict, 'Flat dict is still flat')

    def test_next_ids(self):
        ids = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]
        amount = 5
        iteration = 0

        for chunk in utils.next_ids(ids, amount):
            if iteration == 0 or iteration == 1:
                self.assertEqual(len(chunk), amount, 'This chunk has 5 ids')
            elif iteration == 2:
                self.assertEqual(len(chunk), 2, 'This chunk has 2 ids')
            iteration += 1

    def test_verify_bday(self):
        correct_bdate = '1.1.2000'
        correct_bdate2 = '05.08.1995'
        incorrect_bdate = '18.3'
        wrong_type = 09.12

        self.assertTrue(utils.verify_bday(correct_bdate), 'Correct birth date')
        self.assertTrue(utils.verify_bday(correct_bdate2), 'Correct birth date')
        self.assertFalse(utils.verify_bday(incorrect_bdate), 'Incorrect birth date')
        self.assertIsNone(utils.verify_bday(wrong_type), 'Returns None on the wrong type')


if __name__ == '__main__':
    unittest.main()
