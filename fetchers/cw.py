from network import Network
import datetime
import json


class CW(Network):
    """CW network class"""

    def get_show(self, show_info):
        """
        Get CW show provided
        :param config:
        """
        if not super(self.__class__, self).get_show(show_info):
            return False

        show_title = show_info['show_title']
        show_id = show_info['show_id']

        date = datetime.datetime.today().strftime('%Y%m%d')
        base_url = "http://www.cwtv.com/shows/{0}/?play=".format(show_id)
        show_url = "http://images.cwtv.com/data/r_{0}000/videos/{1}/data.js".format(date, show_id)

        response = self.caller.request_data({"url": show_url})
        if response is not False:
            episode_data = {'show': show_title, 'episodes': {}}
            start = response.text.find("{")
            end = response.text.find(";", start, len(response.text))

            if start > -1 and end > -1:
                json_obj = json.loads(response.text[start:end])
                for episode_id, episode_info in json_obj.iteritems():
                    if episode_info['type'] == "Full":
                        season_number = episode_info['season']
                        episode_number = episode_info['episode']
                        if len(episode_number) > 2 and episode_number[:len(season_number)] is season_number:
                            episode_number = episode_number[-2:]

                        episode_string = self.caller.get_episode_string(season_number, [episode_number])

                        filenames = self.caller.get_filenames(show_title, season_number, episode_string)
                        episode_url = "{0}{1}".format(base_url, episode_id)

                        if season_number not in episode_data['episodes']:
                            episode_data['episodes'][season_number] = {}
                        if episode_number not in episode_data['episodes'][season_number]:
                            episode_data['episodes'][season_number][episode_number] = {
                                'url': episode_url,
                                'filenames': filenames
                            }

        self.caller.process_episodes(episode_data)
        return True
