import instaloader
import os


class InstaHelper:

    def __init__(self):
        self.loader = instaloader.Instaloader(dirname_pattern='/downloads/{profile}/{shortcode}',
                                              filename_pattern='{date}',
                                              save_metadata=False,
                                              download_video_thumbnails=False,
                                              quiet=True)

        self.stories_enabled = False
        username = os.getenv('INSTAGRAM_USERNAME')
        password = os.getenv('INSTAGRAM_PASSWORD')
        if '{username}' not in username and '{password}' not in password and len(username) > 0 and len(password) > 0:
            try:
                self.loader.login(username, password)
                self.stories_enabled = True
            except Exception as e:
                print('stories disabled')
                print(e)
        else:
            print('stories disabled')

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
        stories = self.loader.get_stories(userids=[userid])
        for story in stories:
            for storyitem in story.get_items():
                return storyitem.mediaid
        return 0

    def download_post(self, post):
        self.loader.download_post(post, post.shortcode)

    def download_storyitem(self, storyitem):
        self.loader.download_storyitem(storyitem, storyitem.shortcode)

    def get_profile_from_username(self, username):
        return instaloader.Profile.from_username(self.loader.context, username)
