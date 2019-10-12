import re
from copy import deepcopy
from os import path
from typing import Dict, Union, Set

from Poststorm_Imagery import h


class Image:

    original_size_path: Union[bytes, str]  # The relative path from the catalog.csv for the full size image
    small_size_path: Union[bytes, str]  # The relative path from the catalog.csv for the resized version of the image

    skippers: Set[str] = set()  # The number of times this image has been skipped

    # People who have tagged this image and their tags: taggers[user_id] = {'tag_id': 'value'}
    taggers: Dict[str, Dict] = dict()

    def __init__(self, original_size_path: Union[bytes, str], small_size_path: Union[bytes, str]):
        self.original_size_path = original_size_path
        self.small_size_path = small_size_path

    def __str__(self):
        return self.original_size_path

    def get_taggers(self):
        """Simply get a set of users' ids who have tagged this image.

        :return: The people (by id) who have tagged this image
        """
        return self.taggers.keys()

    def add_tag(self, user_id: str, tag: str, content: str) -> None:
        """
        Add a tag to the image under a specific user's name. If the tag already exists either with the same value or
        a different value, automatically update it with the new value.

        :param user_id: The user to add the tag under
        :param tag: The tag id or name to use
        :param content: The value of the tag (e.g. a string or True/False)
        """

        # Make sure this key exists before attempting to access it
        if user_id not in self.get_taggers():
            self.taggers[user_id] = dict()

        # Check if the response matches a boolean's text (must be explicit to prevent coercion of ints like '1' -> True)
        if content.lower() == ('true' or 'false'):
            content = bool(content)

        # Check if the response is an integer and only an integer (explicitly define match to avoid type coercion)
        elif re.fullmatch('\\d+', content):
            content = int(content)

        self.taggers[user_id][tag]: Union[str, bool, int] = content

    def remove_tag(self, user_id: str, tag: str) -> None:
        """
        Remove a tag from the image under a specific user's name. This will add an entry in the taggers dictionary,
        though it may be empty as a result of removing a tag if it was the only tag remaining.

        :param user_id: The user to remove the tag from under
        :param tag: The tag id or name to use
        """

        # Make sure this key exists before attempting to access it
        if user_id not in self.get_taggers():
            self.taggers[user_id] = dict()

        self.taggers[user_id][tag] = None

    def update_tag(self, user_id: str, tag: str, content: str) -> None:
        """
        Same as the add_tag function. See the add_tag function.

        :param user_id: The user to add the tag under
        :param tag: The tag id or name to use
        :param content: The value of the tag (e.g. a string or True/False)
        """
        self.add_tag(user_id=user_id, tag=tag, content=content)

    def save(self):
        """
        Force inclusion of important objects regardless of copy depth of pickle function. This should only be used
        when the object won't be modified anymore and is about to be saved as a pickle.

        :return: The object with copies of un-included objects that are normally excluded when creating a shallow copy
        """

        # Save a copy of the dictionaries when creating a pickle (without this, the dicts will not save in the pickle)
        self.skippers = self.skippers.copy()
        self.taggers = self.taggers.copy()
        return self

    def expanded(self, scope_path: Union[str, bytes]):
        """
        This function allows for making a copy of the object that includes absolute paths (starting all the way from
        root or the file's drive letter all the way to to the file name including the file type suffix. This is
        useful for the runner in order to pass the context that these Python scripts are running in to the program
        running them through the JSON API.

        :param scope_path: The path to concatenate with the relative path in the copied object
        :return: A copy of the Image object that has all path variables expanded to the absolute path of the scope path
        specified
        """
        expanded_copy = deepcopy(x=self)
        expanded_copy.original_size_path = h.validate_and_expand_path(path.join(scope_path, self.original_size_path))
        expanded_copy.small_size_path = h.validate_and_expand_path(path.join(scope_path, self.small_size_path))

        return expanded_copy

    def _sum_tag_values_by_users(self) -> Dict[str, Dict[str, int]]:
        """
        Get a dictionary of tags and a count of how many times users who have tagged the image tagged it with a
        specific value, grouping them by the value they tagged it with. Note that this ignores tags where the value
        is a string, to ignore extra comments and other non-categorical data.

        :return: A dictionary of dictionaries containing the tag's name as the first key, followed by the inner
        dictionary containing the values for that tag and the number of times a user chose that value for the
        specific tag
        """

        tag_totals: Dict[str, Dict[str, int]] = dict()  # tag_totals[tag][value] = <number of user_ids>

        # Create a dictionary that contains all the image's tags and values as well as a count of how many people
        # tagged the image with the same values.

        for user_id in self.get_taggers():
            for tag, value in self.taggers[user_id]:
                if type(value) is not str:

                    if tag_totals[tag] is None:
                        tag_totals[tag] = dict()

                    if tag_totals[tag][str(value)] is None:
                        tag_totals[tag][str(value)] = 0
                    else:
                        tag_totals[tag][str(value)] += 1

        return tag_totals

    def all_user_tags_equal(self) -> bool:
        """
        Compare all the current tags for an image and see if there is a consensus on what tags the images should
        have. This function will only compare values whose types are not strings. This is to avoid comparing tags
        that contain text like the additional notes section that will ultimately vary by user tagging it.

        :return: Whether (True) or not (False) all users' non-string tags have equal values
        :except NotEnoughTaggersError: The number of current taggers for this image is less than 2
        """

        # Make sure there are at least 2 sets of tags to compare (function should not be called otherwise)
        if len(self.get_taggers()) < 2:
            raise NotEnoughTaggersError

        # Total up all the values for each tag grouped by user's id
        tag_totals: Dict[str, Dict[str, int]] = self._sum_tag_values_by_users()

        for tag in tag_totals:

            # If there are users with different responses for a non-string tag
            if len(tag_totals[tag].keys()) > 2:
                return False

        # All tags have exactly one value for each tag name
        return True


class NotEnoughTaggersError(ValueError):
    def __init__(self):
        Exception.__init__(self, 'Tried to compare taggers\' tags when there were less than 2!')
