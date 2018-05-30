class Network(object):
    """Base network class"""

    def __init__(self, caller):
        self.caller = caller
        self.tvdb_episodes_data = None

    def get_show(self, show_info):
        """
        Get show parent class method
        :param show_info:
        :return:
        """
        if 'thetvdb_id' in show_info:
            if 'sanitize_string' in show_info:
                sanitize_string = show_info['sanitize_string']
            else:
                sanitize_string = {}
            sanitize_string["{0}:".format(show_info['show_title'])] = ""
            self.tvdb_episodes_data = self.get_tvdb_episodes_data(
                {'thetvdb_id': show_info['thetvdb_id'], "sanitize_string": sanitize_string})
            if self.tvdb_episodes_data is None:
                return False
        return True

    def get_tvdb_episodes_data(self, args):
        thetvdb_id = None
        if args is not None:
            if 'thetvdb_id' in args:
                thetvdb_id = args['thetvdb_id']
            elif 'show_title' in args:
                series_info = self.caller.thetvdbapi.get_series(args['show_title'])
                if 'id' in series_info:
                    thetvdb_id = series_info['id']

            if 'sanitize_string' in args:
                sanitize_string = args['sanitize_string']
            else:
                sanitize_string = {}

        if thetvdb_id is None:
            self.caller.logger.warning("Unable to get series episodes from thetvdb")
            return None
        else:
            return self.caller.thetvdbapi.get_series_episodes_by_name(thetvdb_id, sanitize_string)
