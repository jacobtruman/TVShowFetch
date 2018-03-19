import json


class CBS:

    def __init__(self, caller):
        self.caller = caller

    def get_show(self, show_info):
        """
        Get CBS show provided
        :param config:
        """
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
                    season_number = record['season_number']
                    episode_number = record['episode_number']
                    episode_url = "{0}{1}".format(base_url, record['url'])

                    if ',' in episode_number:
                        episode_numbers = episode_number.split(",")
                        eps = []
                        first_episode_number = None
                        last_episode_number = None
                        for episode_number in episode_numbers:
                            this_episode_number = episode_number.trim()
                            if first_episode_number is None:
                                first_episode_number = this_episode_number

                            if last_episode_number is not None and (
                                    this_episode_number - last_episode_number) != 1:
                                self.caller.logger.set_prefix("[ {0} ][ {1} ]".format(show_title, season_number))
                                self.caller.add_to_errors(
                                    "Non-sequential episodes ({0} - {1}) - skipping".format(last_episode_number,
                                                                                            this_episode_number))
                                skip = True
                                break

                            last_episode_number = this_episode_number

                        if skip:
                            continue

                        eps.append(first_episode_number.zfill(2))
                        eps.append(last_episode_number.zfill(2))

                        episode_string = '-'.join(eps)
                    else:
                        season = season_number.zfill(2)
                        episode = episode_number.zfill(2)
                        episode_string = "S{0}E{1}".format(season, episode)

                    filename = self.caller.get_filename(show_title, season_number, episode_string)

                    if season_number not in episode_data['episodes']:
                        episode_data['episodes'][season_number] = {}
                    if episode_number not in episode_data['episodes'][season_number]:
                        episode_data['episodes'][season_number][episode_number] = {'filename': filename,
                                                                                   'url': episode_url}

            self.caller.process_episodes(episode_data)
