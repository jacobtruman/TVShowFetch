from network import Network
from bs4 import BeautifulSoup


class CBC(Network):
    """CBC network class"""

    def get_show(self, show_info):
        """
        Process CBC show provided
        :param show_info:
        """
        if not super(self.__class__, self).get_show(show_info):
            return False

        base_url = "http://www.cbc.ca"
        show_title = show_info['show_title']
        show_id = show_info['show_id']
        show_url = "{0}/{1}/episodes/season1".format(base_url, show_id)

        response = self.caller.request_data({"url": show_url})
        if response is not False:
            seasons = {}
            episode_data = {'show': show_title, 'episodes': {}}
            base_dom = BeautifulSoup(response.text, 'html.parser')
            elements = base_dom.find_all('div')
            for element in elements:
                if 'class' in element.attrs and 'seasons' in element['class']:
                    links = element.find_all('a')
                    for link in links:
                        season_url = "{0}{1}".format(base_url, link['href'])
                        season_number = link.text.replace("Season ", "")
                        if season_number not in seasons:
                            seasons[season_number] = season_url

            season_numbers = seasons.keys()
            if self.caller.latest:
                season_numbers = [max(season_numbers, key=int)]
            else:
                season_numbers.sort(key=int)

            for season_number in season_numbers:
                episode_pages = {}
                season_len = len(str(season_number))
                season_page_data = self.caller.request_data({"url": seasons[season_number]})
                if season_page_data is not False:
                    season_dom = BeautifulSoup(season_page_data.text, 'html.parser')
                    list_items = season_dom.find_all('li')
                    for list_item in list_items:
                        if 'class' in list_item.attrs and 'episode' in list_item['class']:
                            links = list_item.find_all('a')
                            for link in links:
                                episode_page_url = "{0}{1}".format(base_url, link['href'])
                                episode_spans = link.find_all('span')
                                for span in episode_spans:
                                    episode_num_date = span.text.strip().split(" ")
                                    episode_number = int(episode_num_date[0][season_len:])

                                if episode_number not in episode_pages:
                                    episode_pages[episode_number] = episode_page_url

                episode_numbers = episode_pages.keys()
                if self.caller.latest:
                    episode_numbers = [max(episode_numbers, key=int)]
                else:
                    episode_numbers.sort(key=int)
                for episode_number in episode_numbers:
                    episode_page_data = self.caller.request_data({"url": episode_pages[episode_number]})
                    if episode_page_data is not False:
                        episode_dom = BeautifulSoup(episode_page_data.text, 'html.parser')
                        divs = episode_dom.find_all('div')
                        for div in divs:
                            if 'class' in div.attrs and 'responsive-container' in div['class']:
                                episode_links = div.find_all('a')
                                for episode_link in episode_links:
                                    season = season_number.zfill(2)
                                    episode = str(episode_number).zfill(2)
                                    episode_string = "S{0}E{1}".format(season, episode)

                                    episode_url = "{0}{1}".format(base_url, episode_link['href'])
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
