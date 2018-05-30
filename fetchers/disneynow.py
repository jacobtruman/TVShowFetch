from network import Network
from tv_show_fetch import utils

from bs4 import BeautifulSoup


class DisneyNow(Network):
    """DisneyNow network class"""

    def get_show(self, show_info):
        """
        Process DisneyNow show provided
        :param show_info:
        """
        if not super(self.__class__, self).get_show(show_info):
            return False

        base_url = "https://disneynow.go.com"
        show_title = show_info['show_title']
        show_url = "{0}/shows/{1}".format(base_url, show_info['show_id'])

        sanitize_string = super(self.__class__, self).get_sanitize_string(show_info)

        response = self.caller.request_data({"url": show_url})
        if response is not False:
            episode_data = {'show': show_title, 'episodes': {}}
            base_dom = BeautifulSoup(response.text, 'html.parser')
            menu_elements = base_dom.find_all('div')
            for menu_element in menu_elements:
                if 'class' in menu_element.attrs and 'showmenu-items-container-wrap' in menu_element['class']:
                    menu_links = menu_element.find_all('a')
                    for menu_link in menu_links:
                        if "season" in menu_link.text.lower():
                            season_url = menu_link.attrs['href']
                            season_number = season_url.split('-')[-1].lstrip('0')
                            contents = self.caller.request_data({"url": "{0}{1}".format(base_url, season_url)})
                            season_dom = BeautifulSoup(contents.text, 'html.parser')

                            episode_divs = season_dom.find_all('div')
                            for episode_div in episode_divs:
                                if 'data-video-type' in episode_div.attrs and episode_div['data-video-type'] == 'lf':
                                    if 'data-title' in episode_div.attrs:
                                        title = utils.sanitize_string(episode_div['data-title'], sanitize_string)
                                        title_lower = title.lower()
                                        if title_lower in self.tvdb_episodes_data:
                                            record = self.tvdb_episodes_data[title_lower]
                                            episode_number = record['episode_number']

                                            if 'class' in episode_div.attrs and 'locked' not in episode_div['class']:
                                                links = episode_div.find_all('a')
                                                for link in links:
                                                    if 'class' in link.attrs and 'disneynow-icon-play' in link.attrs['class']:
                                                        episode_string = self.caller.get_episode_string(season_number, [episode_number])

                                                        filenames = self.caller.get_filenames(show_title, season_number, episode_string)
                                                        episode_url = "{0}{1}".format(base_url, link.attrs['href']).strip()

                                                        if season_number not in episode_data['episodes']:
                                                            episode_data['episodes'][season_number] = {}
                                                        if episode_number not in episode_data['episodes'][season_number]:
                                                            episode_data['episodes'][season_number][episode_number] = {
                                                                'url': episode_url,
                                                                'filenames': filenames
                                                            }

                                        else:
                                            self.caller.logger.set_prefix("[ {0} ]".format(show_title))
                                            self.caller.add_to_errors("Unable to find information for episode '{0}' - skipping".format(title))

            self.caller.process_episodes(episode_data)
        else:
            self.caller.logger.error("Request returned False: {0}".format(show_url))
        return True
