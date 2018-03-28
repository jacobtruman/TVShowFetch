from network import Network
from tv_show_fetch import utils
import json


class NickJr(Network):
    """Nick Jr network class"""

    def get_show(self, show_info):
        """
        Get Nick Jr show provided
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

        sanitize_string['{0}: '.format(show_title)] = ''
        sanitize_string['.'] = ''

        episode_data = {'show': show_title, 'episodes': {}}

        base_url = "http://www.nickjr.com"
        show_url = "{0}/data/propertyVideosStreamPage.json".format(base_url)

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
                                        fail = False
                                        title = utils.sanitize_string(data['title'], sanitize_string)
                                        season_number = 0
                                        episode_url = "{0}{1}".format(base_url, data['url'])
                                        episode_numbers = []
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
                                                        self.caller.add_to_errors(
                                                            "Cross-season episode '{0}' - skipping".format(title))
                                                        fail = True
                                                        break

                                                    this_episode_number = record['episode_number'].strip()

                                                    if first_episode_number is None:
                                                        first_episode_number = this_episode_number
                                                        first_episode_title = title

                                                    if last_episode_number is not None and (
                                                            this_episode_number - last_episode_number) != 1:
                                                        self.caller.logger.set_prefix(
                                                            "[ {0} ][ {1} ]".format(show_title, season_number))
                                                        self.caller.logger.warning(
                                                            "Non-sequential episodes ({0}) ({1} - {2}) - skipping".format(
                                                                full_title,
                                                                last_episode_number,
                                                                this_episode_number))
                                                        last_filenames = self.caller.get_filenames(show_title,
                                                                                                   season_number,
                                                                                                   self.caller.get_episode_string(
                                                                                                       season_number,
                                                                                                       [
                                                                                                           last_episode_number]))

                                                        this_filenames = self.caller.get_filenames(show_title,
                                                                                                   season_number,
                                                                                                   self.caller.get_episode_string(
                                                                                                       season_number,
                                                                                                       [
                                                                                                           this_episode_number]))
                                                        if not self.caller.file_exists(last_filenames['final']):
                                                            self.caller.logger.error(
                                                                "First non-sequential episode ({0}) ({1}) missing - {2}".format(
                                                                    first_episode_title,
                                                                    last_episode_number,
                                                                    episode_url))
                                                        if not self.caller.file_exists(this_filenames['final']):
                                                            self.caller.logger.error(
                                                                "Second non-sequential episode ({0}) ({1}) missing - {2}".format(
                                                                    title,
                                                                    this_episode_number,
                                                                    episode_url))

                                                        self.caller.logger.reset_prefix()
                                                        fail = True
                                                        break

                                                    last_episode_number = this_episode_number
                                                else:
                                                    self.caller.logger.set_prefix("[ {0} ]".format(show_title))
                                                    self.caller.add_to_errors(
                                                        "Unable to find information for episode (MULTI) '{0}' of '{1}' - skipping".format(
                                                            title, full_title))
                                                    fail = True
                                                    break

                                            if first_episode_number is not None:
                                                episode_numbers.append(first_episode_number)
                                            if last_episode_number is not None:
                                                episode_numbers.append(last_episode_number)
                                        else:
                                            title_lower = title.lower()
                                            if title_lower in self.tvdb_episodes_data:
                                                record = self.tvdb_episodes_data[title_lower]
                                                season_number = record['season_number']
                                                episode_numbers.append(record['episode_number'])
                                            else:
                                                self.caller.logger.set_prefix("[ {0} ]".format(show_title))
                                                self.caller.add_to_errors(
                                                    "Unable to find information for episode (SINGLE) '{0}' - skipping".format(
                                                        title))
                                                continue
                                        if not fail:
                                            episode_number = episode_numbers[-1]
                                            episode_string = self.caller.get_episode_string(season_number,
                                                                                            episode_numbers)
                                            filenames = self.caller.get_filenames(show_title, season_number,
                                                                                  episode_string)

                                            if season_number not in episode_data['episodes']:
                                                episode_data['episodes'][season_number] = {}
                                            if episode_number not in episode_data['episodes'][season_number]:
                                                episode_data['episodes'][season_number][episode_number] = {
                                                    'url': episode_url,
                                                    'filenames': filenames
                                                }

                more = json_obj['pagination']['moreItems']
                offset += json_obj['pagination']['count']

        self.caller.process_episodes(episode_data)
        return True
