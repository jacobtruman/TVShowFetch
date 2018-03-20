from network import Network
from tv_show_fetch import utils
import json


class NickJr(Network):

    def get_show(self, show_info):
        """
        Get Nick Jr show provided
        :param config:
        """
        show_title = show_info['show_title']
        show_id = show_info['show_id']
        episode_data = {'show': show_title, 'episodes': {}}

        base_url = "http://www.nickjr.com"
        show_url = "{0}/data/propertyVideosStreamPage.json".format(base_url)

        self.tvdb_episodes_data = self.get_tvdb_episodes_data({'thetvdb_id': show_info['thetvdb_id']})
        if self.tvdb_episodes_data is None:
            return

        offset = 0
        more = True
        while more:
            params = {'apiKey': 'nickjr.com', 'urlKey': show_id, 'page': 1, 'reverseCronStartIndex': offset,
                      'blockIndex': 1, 'breakpoint': 'stream-large'}

            response = self.caller.request_data({"url": show_url, 'params': params})
            if response is not False:
                json_obj = json.loads(response.text)
                if 'stream' in json_obj:
                    for chunk in json_obj['stream']:
                        if 'items' in chunk:
                            for item in chunk['items']:
                                if 'data' in item:
                                    data = item['data']
                                    if data['mediaType'] != 'episode' or data['authRequired']:
                                        continue
                                    else:
                                        title = utils.sanitize_string(data['title'],
                                                                      {'{0}: '.format(data['seriesTitle']): '', '.': ''})
                                        season_number = 0
                                        episode_url = "{0}{1}".format(base_url, data['url'])
                                        filename = None
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
                                                        self.caller.logger.set_prefix("[ {0} ][ {1} ]".format(show_title, season_number))
                                                        self.caller.add_to_errors("Cross-season episode '{0}' - skipping".format(title))
                                                        break

                                                    this_episode_number = record['episode_number'].strip()

                                                    if first_episode_number is None:
                                                        first_episode_number = this_episode_number

                                                    if last_episode_number is not None and (this_episode_number - last_episode_number) != 1:
                                                        self.caller.logger.set_prefix("[ {0} ][ {1} ]".format(show_title, season_number))
                                                        self.caller.add_to_errors("Non-sequential episodes ({0}) ({1} - {2}) - skipping".format(full_title, last_episode_number, this_episode_number));
                                                        break

                                                    last_episode_number = this_episode_number
                                                else:
                                                    self.caller.logger.set_prefix("[ {0} ]".format(show_title))
                                                    self.caller.add_to_errors("Unable to find information for episode (MULTI) '{0}' of '{1}' - skipping".format(title, full_title))
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
                                                self.caller.add_to_errors("Unable to find information for episode (SINGLE) '{0}' - skipping".format(title))
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

                more = json_obj['pagination']['moreItems']
                offset += json_obj['pagination']['count']

        self.caller.process_episodes(episode_data)
