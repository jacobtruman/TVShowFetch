from network import Network
from bs4 import BeautifulSoup
from tv_show_fetch import utils

import json


class HGTV(Network):
    """HGTV network class"""

    def get_show(self, show_info):
        """
        Process HGTV show provided
        :param show_info:
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

        base_url = 'http://www.hgtv.com'
        base_url_media = 'http://sniidevices.scrippsnetworks.com'

        page = 1
        max_page = 0

        done = False
        while not done:
            show_url = '{0}/shows/{1}/videos/p/{2}'.format(base_url, show_id, page)

            response = self.caller.request_data({"url": show_url})
            if max_page == 0:
                if response is not False:
                    base_dom = BeautifulSoup(response.text, 'html.parser')
                    elements = base_dom.find_all('section')
                    for element in elements:
                        if 'class' in element.attrs and 'o-Pagination' in element['class']:
                            list_items = element.find_all('li')
                            for list_item in list_items:
                                if 'class' in list_item.attrs and 'o-Pagination__a-ListItem' in list_item['class']:
                                    links = list_item.find_all('a')
                                    for link in links:
                                        try:
                                            max_page = int(link.text.strip())
                                        except ValueError:
                                            pass

            divs = base_dom.find_all('div')
            for div in divs:
                if 'data-deferred-module' in div.attrs and div['data-deferred-module'] == 'video':
                    json_obj = json.loads(div.text)
                    if 'channels' in json_obj and 'videos' in json_obj['channels'][0]:
                        for video in json_obj['channels'][0]['videos']:
                            if video['length'] > 1800:
                                vid_id = video['nlvid']
                                vid_sub_id = vid_id[0:4]
                                title = utils.sanitize_string(video['title'], sanitize_string)
                                title_lower = title.lower()

                                if title_lower in self.tvdb_episodes_data:
                                    season_number = self.tvdb_episodes_data[title_lower]['season_number']
                                    episode_number = self.tvdb_episodes_data[title_lower]['episode_number']

                                    season = str(season_number).zfill(2)
                                    episode = str(episode_number).zfill(2)
                                    episode_string = "S{0}E{1}".format(season, episode)

                                    filename = self.caller.get_filename(show_title, season_number, episode_string)
                                    episode_url = "{0}/{1}/{2}_6.mp4".format(base_url_media, vid_sub_id, vid_id)

                                    if season_number not in episode_data['episodes']:
                                        episode_data['episodes'][season_number] = {}
                                    if episode_number not in episode_data['episodes'][season_number]:
                                        episode_data['episodes'][season_number][episode_number] = {
                                            'filename': filename,
                                            'url': episode_url}
                    break
            page += 1
            if page > max_page:
                done = True

        self.caller.process_episodes(episode_data)
        return True
