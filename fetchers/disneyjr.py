from network import Network
from tv_show_fetch import utils
import json


class DisneyJr(Network):

    def get_show(self, show_info):
        """
        Get Disney Jr show provided
        :param config:
        """
        if not super(self.__class__, self).get_show(show_info):
            return False

        show_title = show_info['show_title']
        show_id = show_info['show_id']

        if 'sanitize_string' in show_info:
            sanitize_string = show_info['sanitize_string']
        else:
            sanitize_string = {}

        episode_data = {'show': show_title, 'episodes': {}}

        api_base_url = 'https://api.presentation.abc.go.com'
        base_url = 'http://watchdisneyjunior.go.com'

        start = 0
        max = 50

        show_url = '{0}/api/ws/presentation/v2/module/617.json'.format(api_base_url)
        params = {'brand': '008', 'device': '001', 'authlevel': 0, 'start': start, 'size': max, 'show': show_id}

        response = self.caller.request_data({"url": show_url, 'params': params})
        if response is not False:
            json_obj = json.loads(response.text)
            if 'tilegroup' in json_obj and 'tiles' in json_obj['tilegroup'] and 'tile' in json_obj['tilegroup']['tiles']:
                tile_count = len(json_obj['tilegroup']['tiles']['tile'])
                self.caller.logger.info("{0} items found".format(tile_count))
                if tile_count > 0:
                    for item in json_obj['tilegroup']['tiles']['tile']:
                        if 'accesslevel' in item and int(item['accesslevel']) != 0:
                            continue
                        title = utils.sanitize_string(item['video']['title'], sanitize_string)
                        season_number = 0
                        episode_url = "{0}{1}".format(base_url, item['link']['value'])
                        eps = []
                        if '/' in title:
                            full_title = title
                            titles = title.split('/')
                            first_episode_number = None
                            last_episode_number = None
                            for title in titles:
                                title = utils.sanitize_string(title)
                                title_lower = title.lower()
                                if title_lower in self.tvdb_episodes_data:
                                    record = self.tvdb_episodes_data[title_lower]
                                    if season_number == 0:
                                        season_number = record['season_number']
                                    elif season_number != record['season_number']:
                                        self.caller.logger.set_prefix(
                                            "[ {0} ][ {1} ]".format(show_title, season_number))
                                        self.caller.add_to_errors("Cross-season episode '{0}' - skipping".format(title))
                                        break

                                    this_episode_number = record['episode_number'].strip()

                                    if first_episode_number is None:
                                        first_episode_number = this_episode_number

                                    if last_episode_number is not None and (
                                            this_episode_number - last_episode_number) != 1:
                                        self.caller.logger.set_prefix(
                                            "[ {0} ][ {1} ]".format(show_title, season_number))
                                        self.caller.add_to_errors(
                                            "Non-sequential episodes ({0}) ({1} - {2}) - skipping".format(full_title,
                                                                                                          last_episode_number,
                                                                                                          this_episode_number))
                                        break

                                    last_episode_number = this_episode_number
                                else:
                                    self.caller.logger.set_prefix("[ {0} ]".format(show_title))
                                    self.caller.add_to_errors(
                                        "Unable to find information for episode (MULTI) '{0}' of '{1}' - skipping".format(
                                            title, full_title))
                                    break

                            if first_episode_number is not None:
                                eps.append(str(first_episode_number).zfill(2))
                            if last_episode_number is not None:
                                eps.append(str(last_episode_number).zfill(2))
                        else:
                            title_lower = title.lower()
                            if title_lower in self.tvdb_episodes_data:
                                record = self.tvdb_episodes_data[title_lower]
                                season_number = record['season_number']
                                eps.append(str(record['episode_number']).zfill(2))
                            else:
                                self.caller.logger.set_prefix("[ {0} ]".format(show_title))
                                self.caller.add_to_errors(
                                    "Unable to find information for episode (SINGLE) '{0}' - skipping".format(title))
                                continue

                        episode_number = '-'.join(eps)
                        season = str(season_number).zfill(2)
                        episode_string = 'S{0}E{1}'.format(season, '-E'.join(eps))
                        filename = self.caller.get_filename(show_title, season_number, episode_string)

                        if season_number not in episode_data['episodes']:
                            episode_data['episodes'][season_number] = {}
                        if episode_number not in episode_data['episodes'][season_number]:
                            episode_data['episodes'][season_number][episode_number] = {
                                'filename': filename,
                                'url': episode_url}

        self.caller.process_episodes(episode_data)
        return True
