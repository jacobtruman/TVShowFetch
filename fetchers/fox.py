from network import Network
import json


class FOX(Network):
    """FOX network class"""

    def get_show(self, show_info):
        """
        Get FOX show provided
        :param config:
        """
        if not super(self.__class__, self).get_show(show_info):
            return False

        show_title = show_info['show_title']
        show_id = show_info['show_id']

        episode_data = {'show': show_title, 'episodes': {}}

        base_url = "https://www.fox.com/watch"
        show_url = "https://api.fox.com/fbc-content/v1_4/screens/series-detail/{0}/".format(show_id)

        response = self.caller.request_data({"url": show_url, 'headers': show_info['headers']})
        if response is not False:
            json_obj = json.loads(response.text)
            seasons = json_obj['panels']['member'][1]['items']['member']
            for season in seasons:
                if 'episodes' in season:
                    season_number = str(season['seasonNumber'])
                    episodes_url = season['episodes']['@id']
                    season_episodes = self.caller.request_data({"url": episodes_url, 'headers': show_info['headers']})
                    if season_episodes is not False:
                        seasons_json_obj = json.loads(season_episodes.text)
                        for episode_obj in seasons_json_obj['member']:
                            if not episode_obj['requiresAuth'] and episode_obj['isFullEpisode']:
                                episode_number = str(episode_obj['episodeNumber'])
                                season = season_number.zfill(2)
                                episode = episode_number.zfill(2)
                                episode_string = "S{0}E{1}".format(season, episode)

                                filenames = self.caller.get_filenames(show_title, season_number, episode_string)
                                episode_url = "{0}/{1}/".format(base_url, episode_obj['id'])

                                if season_number not in episode_data['episodes']:
                                    episode_data['episodes'][season_number] = {}
                                if episode_number not in episode_data['episodes'][season_number]:
                                    episode_data['episodes'][season_number][episode_number] = {
                                        'url': episode_url,
                                        'filenames': filenames
                                    }

        self.caller.process_episodes(episode_data)
        return True
