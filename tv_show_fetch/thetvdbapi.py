import json
import utils


class TheTVDBApi(object):

    def __init__(self, caller, creds):
        """
        :param creds:
        """
        cred_params = ['apikey', 'userkey', 'username']
        for param in cred_params:
            if param not in creds:
                raise ValueError('{} not provided in creds'.format(param))

        self.creds = creds
        self.caller = caller

        self.base_url = "https://api.thetvdb.com"

        self._token = self._get_api_token()

    def _get_api_token(self):
        headers = {'Content-Type': 'application/json', 'Accept': 'application/json'}

        args = {'url': "{0}/login".format(self.base_url), 'headers': headers, 'data': self.creds, 'method': 'post'}
        if hasattr(self.caller, 'logger'):
            args['logger'] = self.caller.logger

        data = utils.request_data(args)
        if data is not False:
            json_obj = json.loads(data.text)
            if 'token' in json_obj:
                return json_obj['token']
            else:
                self.caller.add_to_errors("TheTVDB login failed - no token found in response")
                return None
        else:
            self.caller.add_to_errors("TheTVDB login failed - response False")
            return None

    def _get_auth_headers(self):
        return {
            'Accept': 'application/json',
            'Authorization': 'Bearer {0}'.format(self._token)
        }

    def get_series(self, series_name):
        headers = self._get_auth_headers()
        params = {'name': series_name}

        args = {'url': "{0}/search/series".format(self.base_url), 'headers': headers, 'params': params}
        if hasattr(self.caller, 'logger'):
            args['logger'] = self.caller.logger

        data = utils.request_data(args)
        if data is not False:
            json_obj = json.loads(data.text)
            if 'data' in json_obj and len(json_obj['data']) > 0:
                return json_obj['data'][0]
            else:
                self.caller.add_to_errors("Unable to find series: {0}".format(series_name))
                return None
        else:
            return None

    def get_series_episodes(self, series_id):
        episodes = []
        page = 1
        headers = self._get_auth_headers()

        args = {'headers': headers}
        if hasattr(self.caller, 'logger'):
            args['logger'] = self.caller.logger

        while page is not None:
            args['params'] = {'page': page}
            args['url'] = "{0}/series/{1}/episodes".format(self.base_url, series_id)

            data = utils.request_data(args)
            if data is not False:
                json_obj = json.loads(data.text)
                page = json_obj['links']['next']
                if 'data' in json_obj:
                    episodes = episodes + json_obj['data']

        return episodes

    def get_series_episodes_by_name(self, series_id):
        episodes_by_name = {}
        episodes = self.get_series_episodes(series_id)
        for episode in episodes:
            if episode['episodeName'] is not None:
                episode_name = utils.sanitize_string(episode['episodeName'])
                if episode_name not in episodes_by_name:
                    episodes_by_name[episode_name] = {'season_number': episode['airedSeason'],
                                                      'episode_number': episode['airedEpisodeNumber']}

        return episodes_by_name
