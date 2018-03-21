from network import Network
import datetime
import time
import urllib
import json


class NBC(Network):
    """NBC network class"""

    def get_show(self, show_info):
        """
        Process NBC show provided
        :param show_info:
        """
        if not super(self.__class__, self).get_show(show_info):
            return False

        base_url = "https://api.nbc.com/v3.14/videos"
        page_size = 50
        show_title = show_info['show_title']

        # tomorrow
        end_date = datetime.date.today() + datetime.timedelta(days=1)

        loop = True
        page_num = 0

        while (loop):
            page_num += 1
            params = {}

            params[
                'fields[videos]'] = "title,type,available,seasonNumber,episodeNumber,expiration,entitlement,tveAuthWindow,nbcAuthWindow,permalink,embedUrl,externalAdId"
            params['include'] = "show.season"
            params['filter[show]'] = show_info['show_id']
            params['filter[available][value]'] = end_date
            params['filter[available][operator]'] = "<"
            params['filter[entitlement][value]'] = "free"
            params['filter[entitlement][operator]'] = "="
            params['filter[type][value]'] = "Full Episode"
            params['filter[type][operator]'] = "="

            params['page[number]'] = page_num
            params['page[size]'] = page_size

            params_string = urllib.urlencode(params).replace("%3D%3D", "=%3D").replace("%3D%3E",
                                                                                       "=%3E").replace("%3D%3C",
                                                                                                       "=%3C").replace(
                "%5D%3D", "%5D=").replace("include%3D", "include=")

            show_url = "{0}?{1}".format(base_url, params_string)

            response = self.caller.request_data({"url": show_url})
            if response is not False:
                json_obj = json.loads(response.text)

                episode_data = {'show': show_title, 'episodes': {}}

                now = int(time.time())
                if 'data' in json_obj:
                    if len(json_obj['data']) < page_size:
                        loop = False

                    for record in json_obj['data']:
                        attributes = record['attributes']
                        entitlement = attributes['entitlement']

                        if entitlement != "free":
                            continue

                        get = False
                        for window in attributes['nbcAuthWindow']:
                            if window['type'] != "free":
                                continue
                            end_ts = int(time.mktime(time.strptime(window['end'], '%Y-%m-%dT%H:%M:%S+%f')))
                            if now < end_ts:
                                get = True

                        if get:
                            season_number = attributes['seasonNumber']
                            episode_number = attributes['episodeNumber']
                            season = season_number.zfill(2)
                            episode = episode_number.zfill(2)
                            episode_string = "S{0}E{1}".format(season, episode)

                            filenames = self.caller.get_filenames(show_title, season_number, episode_string)
                            episode_url = attributes['permalink']

                            if season_number not in episode_data['episodes']:
                                episode_data['episodes'][season_number] = {}
                            if episode_number not in episode_data['episodes'][season_number]:
                                episode_data['episodes'][season_number][episode_number] = {
                                    'url': episode_url,
                                    'filenames': filenames
                                }

                self.caller.process_episodes(episode_data)
        return True
