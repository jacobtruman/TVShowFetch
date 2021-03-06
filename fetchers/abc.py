from network import Network

from bs4 import BeautifulSoup


class ABC(Network):
    """ABC network class"""

    def get_show(self, show_info):
        """
        Process ABC show provided
        :param show_info:
        """
        if not super(self.__class__, self).get_show(show_info):
            return False

        base_url = "http://abc.go.com"
        show_title = show_info['show_title']
        show_url = "{0}/shows/{1}/episode-guide/".format(base_url, show_info['show_id'])

        response = self.caller.request_data({"url": show_url})
        if response is not False:
            episode_data = {'show': show_title, 'episodes': {}}
            base_dom = BeautifulSoup(response.text, 'html.parser')
            elements = base_dom.find_all('select')
            for element in elements:
                if element['name'] == 'blog-select':
                    seasons = element.find_all('option')
                    for season in seasons:
                        season_url = season['value']
                        season_number = season_url.split('-')[-1].lstrip('0')
                        contents = self.caller.request_data({"url": "{0}{1}".format(base_url, season_url)})
                        season_dom = BeautifulSoup(contents.text, 'html.parser')
                        season_divs = season_dom.find_all('div')
                        for season_div in season_divs:
                            if 'data-sm-type' in season_div.attrs and season_div['data-sm-type'] == 'episode':
                                links = season_div.find_all('a')
                                watch = False
                                for link in links:
                                    if link.text.lower() == 'watch':
                                        watch = True
                                        break
                                if watch:
                                    episode_divs = season_div.find_all('div')
                                    locked = False
                                    for episode_div in episode_divs:
                                        if 'class' in episode_div.attrs and 'locked' in episode_div['class']:
                                            locked = True
                                            break

                                    if not locked:
                                        spans = season_div.find_all('span')
                                        for span in spans:
                                            if 'class' in span.attrs and 'episode-number' in span['class']:
                                                episode_number = span.text.replace("E", "", ).strip()
                                                break

                                        episode_string = self.caller.get_episode_string(season_number, [episode_number])

                                        filenames = self.caller.get_filenames(show_title, season_number, episode_string)
                                        episode_url = "{0}{1}".format(base_url, season_div.attrs['data-url']).strip()

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
