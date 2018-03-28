from network import Network
import json


class CBS(Network):
    """CBS network class"""

    def get_show(self, show_info):
        """
        Get CBS show provided
        :param config:
        """
        if not super(self.__class__, self).get_show(show_info):
            return False

        base_url = "https://www.cbs.com"
        offset = 0
        limit = 100
        show_title = show_info['show_title']

        if 'single_season' in show_info and show_info['single_season']:
            show_url = "{0}/carousels/videosBySection/{1}/offset/{2}/limit/{3}/xs/0/".format(base_url,
                                                                                             show_info[
                                                                                                 'show_id'],
                                                                                             offset, limit)
        else:
            show_url = "{0}/carousels/shows/{1}/offset/{2}/limit/{3}/".format(base_url, show_info['show_id'],
                                                                              offset,
                                                                              limit)

        response = self.caller.request_data({"url": show_url})
        if response is not False:
            json_obj = json.loads(response.text)

            episode_data = {'show': show_title, 'episodes': {}}

            if 'result' in json_obj and 'data' in json_obj['result']:
                for record in json_obj['result']['data']:
                    skip = False
                    episode_numbers = []
                    season_number = record['season_number']
                    episode_number = record['episode_number']
                    episode_url = "{0}{1}".format(base_url, record['url'])

                    if ',' in episode_number:
                        first_episode_number = None
                        last_episode_number = None
                        for episode_number in episode_number.split(","):
                            this_episode_number = episode_number.trim()
                            if first_episode_number is None:
                                first_episode_number = this_episode_number

                            if last_episode_number is not None and (
                                    this_episode_number - last_episode_number) != 1:
                                self.caller.logger.set_prefix("[ {0} ][ {1} ]".format(show_title, season_number))
                                self.caller.logger.warning(
                                    "Non-sequential episodes ({0} - {1}) - skipping".format(last_episode_number,
                                                                                            this_episode_number))

                                last_filenames = self.caller.get_filenames(show_title, season_number,
                                                                           self.caller.get_episode_string(
                                                                               season_number,
                                                                               [last_episode_number]))

                                this_filenames = self.caller.get_filenames(show_title, season_number,
                                                                           self.caller.get_episode_string(
                                                                               season_number,
                                                                               [this_episode_number]))
                                if not self.caller.file_exists(last_filenames['final']):
                                    self.caller.logger.error(
                                        "First non-sequential episode ({0}) missing - {1}".format(
                                            last_episode_number,
                                            episode_url))
                                if not self.caller.file_exists(this_filenames['final']):
                                    self.caller.logger.error(
                                        "Second non-sequential episode ({0}) missing - {1}".format(
                                            this_episode_number,
                                            episode_url))

                                self.caller.logger.reset_prefix()

                                skip = True
                                break

                            last_episode_number = this_episode_number

                        if skip:
                            continue

                        episode_numbers.append(first_episode_number)
                        episode_numbers.append(last_episode_number)
                    else:
                        episode_numbers.append(episode_number)

                    episode_string = self.caller.get_episode_string(season_number, episode_numbers)
                    filenames = self.caller.get_filenames(show_title, season_number, episode_string)

                    if season_number not in episode_data['episodes']:
                        episode_data['episodes'][season_number] = {}
                    if episode_number not in episode_data['episodes'][season_number]:
                        episode_data['episodes'][season_number][episode_number] = {
                            'url': episode_url,
                            'filenames': filenames
                        }

            self.caller.process_episodes(episode_data)
        else:
            self.caller.logger.error("Request returned False: {0}".format(show_url))
        return True
