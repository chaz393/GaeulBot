import instaloader
import os
from ItemType import ItemType


class InstaHelper:

    def __init__(self):
        self.loader = instaloader.Instaloader(dirname_pattern='/downloads/{profile}/{target}/{shortcode}',
                                              filename_pattern='{date}',
                                              save_metadata=False,
                                              download_video_thumbnails=False,
                                              quiet=True)
        self.logged_in = False

    def try_login(self, username, password):
        self.loader.login(username, password)
        self.logged_in = True
        print("successfully logged into insta with username {0}".format(username))

    def getMediaId(self, item):
        return item.mediaid

    def get_posts(self, user, last_id):
        profile = instaloader.Profile.from_username(self.loader.context, user)
        posts = []
        for post in profile.get_posts():
            if post.mediaid <= last_id:
                break
            posts.append(post)
        posts.sort(key=self.getMediaId)
        return posts

    def get_stories_for_user(self, userid, last_id):
        stories = []
        for story in self.loader.get_stories(userids=[userid]):
            for storyitem in story.get_items():
                if storyitem.mediaid <= last_id:
                    break
                stories.append(storyitem)
        stories.sort(key=self.getMediaId)
        return stories

    def get_post_from_shortcode(self, shortcode):
        return instaloader.Post.from_shortcode(self.loader.context, shortcode)

    def get_latest_post_id_from_ig(self, profile):
        for post in profile.get_posts():
            return post.mediaid
        return 0

    def get_latest_story_id_from_ig(self, userid):
        if self.logged_in:
            stories = self.loader.get_stories(userids=[userid])
            for story in stories:
                for storyitem in story.get_items():
                    return storyitem.mediaid
        return 0

    def download_post(self, post):
        self.loader.download_post(post, ItemType.POST.get_name())

    def download_storyitem(self, storyitem):
        self.loader.download_storyitem(storyitem, ItemType.STORY.get_name())

    def get_profile_from_username(self, username):
        return instaloader.Profile.from_username(self.loader.context, username)

    @staticmethod
    def login_info_is_valid(username, password):
        valid = username is not None and password is not None \
                and len(username) > 0 and len(password) > 0 \
                and '{username}' not in username and '{password}' not in password
        if not valid:
            if username is None or not len(username) > 0 or '{username}' in username:
                print("instagram username is invalid. check env file")
            if password is None or not len(password) > 0 or '{password}' in password:
                print("instagram password is invalid. check env file")
        return valid
