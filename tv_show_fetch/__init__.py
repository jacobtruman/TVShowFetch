import os.path
import utils
import logger
import thetvdbapi
import youtube_dl
import sys

from fetchers import *


class TVShowFetch(object):

    def __init__(self, args):
        """
        Class to fetch TV shows from network websites
        :param args:
        """
        if 'base_config' not in args:
            raise ValueError('base_config not provided')
        elif 'tvdb' not in args['base_config']:
            raise ValueError('tvdb not provided in base_config')

        self.home_dir = os.path.expanduser("~")
        self.base_dir = '{0}/TVShows'.format(self.home_dir)
        self.title_filter = ""
        self.latest = True
        self.verbose = True
        self.execute = False

        # override any default settings defined in params
        for arg in args:
            self.__dict__[arg] = args[arg]

        self.logger = logger.Logger({'colorize': True})
        self.thetvdbapi = thetvdbapi.TheTVDBApi(self, args['base_config']['tvdb'])
        self.downloaded = []
        self.extension = ".mp4"

        self.ydl_opts = {
            'format': self.extension.replace(".", ""),
            'verbose': True,
            'nocheckcertificate': True,
            'progress_hooks': [self.ydl_progress_hook],
            # 'ignoreerrors': True,
        }

    def ydl_progress_hook(self, d):
        """
        Handle progress points in the youtube-dl process
        :param d:
        :return:
        """
        # if d['status'] == 'downloading':
        # print('ETA: {0}\tTime Elapsed: {1}\tSpeed (bytes/second): {2}'.format(d['eta'], d['elapsed'], d['speed']))
        if d['status'] == 'finished':
            print('Done downloading, now compressing...')

    def process_config(self, config):
        """
        Process the config provided
        :param config:
        """
        network = config['network'].replace(' ', '')
        module_name = "fetchers.{0}".format(network.lower())
        if module_name in sys.modules:
            method = "get_show"
            module = getattr(sys.modules[module_name], network)(self)
            if hasattr(module, method):
                shows = self.get_active_shows(config['shows'])
                count = len(shows)
                if count > 0:
                    num = 0
                    for show_info in shows:
                        num += 1
                        self.logger.info(
                            "Processing show {0} / {1} :: '{2}'".format(num, count, show_info['show_title']))
                        if 'apiKey' in config:
                            show_info['headers'] = {
                                'apiKey': config['apiKey']
                            }

                        getattr(module, method)(show_info)
                        self.logger.reset_prefix()
            else:
                self.add_to_errors("Module '{0}' does not have method '{1}'".format(module_name, method))
        else:
            self.add_to_errors("Module '{0}' does not exist".format(module_name))

    def get_active_shows(self, shows):
        """
        Get active shows from config provided
        :param shows:
        :return: List of active show configs
        """
        active_shows = []
        for show_info in shows:
            if 'active' not in show_info or show_info['active'] is False:
                self.logger.info("{0} is not active - skipping".format(show_info['show_title']))
            elif self.title_filter is not None and self.title_filter not in show_info['show_title']:
                self.logger.warning("{0} does not match filter provided: '{1}' - skipping".format(
                    show_info['show_title'],
                    self.title_filter))
            else:
                active_shows.append(show_info)

        self.logger.info("Shows to be processed: {0}".format(len(active_shows)))

        return active_shows

    def request_data(self, args=None):
        if 'logger' not in args:
            args['logger'] = self.logger
        return utils.request_data(args)

    def process_episodes(self, episode_data):
        """
        Process episodes found provided in episode_data
        :param episode_data:
        """
        if 'episodes' in episode_data and 'show' in episode_data:
            show_title = episode_data['show']
            episodes = episode_data['episodes']

            self.logger.set_prefix("\t[ {0} ]".format(show_title))
            if self.latest:
                latest = self.get_latest_episode(episodes)
                self.logger.info("Processing latest episode")
                if latest is not False:
                    max_season, max_episode = latest
                    self.logger.set_prefix("\t[ {0} ][ Season {1} ][ Episode {2} ]".format(show_title, max_season,
                                                                                           max_episode))
                    latest_episode = episodes[max_season][max_episode]
                    self.process_url(latest_episode['url'], latest_episode['filename'])
                else:
                    self.logger.info("[ {0} ] Unable to get the latest episode".format(show_title))
            else:
                self.logger.info("Processing episodes from {0} seasons".format(len(episodes)))
                season_numbers = episodes.keys()
                season_numbers.sort(key=int)
                for season_num in season_numbers:
                    episode_numbers = episodes[season_num].keys()
                    # TODO: fix issue when multi-episode (ex: 35-36)
                    # invalid literal for int() with base 10: '35-36'
                    episode_numbers.sort(key=int)
                    self.logger.set_prefix("\t[ {0} ][ Season {1} ]".format(show_title, season_num))
                    self.logger.info("Processing {0} episodes".format(len(episode_numbers)))
                    for episode_num in episode_numbers:
                        episode = episodes[season_num][episode_num]
                        self.logger.set_prefix("\t[ {0} ][ Season {1} ][ Episode {2} ]".format(show_title, season_num,
                                                                                               episode_num))
                        self.process_url(episode['url'], episode['filename'])
        else:
            self.logger.info("Episode data structure provided is missing required data")

            self.logger.reset_prefix()

    @staticmethod
    def get_latest_episode(episodes):
        """
        Get the latest episode from episodes provided
        :param episodes:
        :return: Latest episode
        """
        ret = False
        if len(episodes) > 0:
            season_numbers = episodes.keys()
            season_numbers.sort(key=int, reverse=True)
            max_season = season_numbers[0]
            episode_numbers = episodes[max_season].keys()
            episode_numbers.sort(key=int, reverse=True)
            max_episode = episode_numbers[0]

            ret = [max_season, max_episode]

        return ret

    def process_url(self, url, filename):
        """
        Process show url provided
        :param url:
        :param filename:
        :return: Boolean
        """
        temp_filename = filename.replace(self.extension, ".temp{}".format(self.extension))
        ydl_opts = self.ydl_opts.copy()
        ydl_opts['outtmpl'] = filename
        ydl_opts['postprocessors'] = [
            {
                'key': 'ExecAfterDownload',
                'exec_cmd': "ffmpeg -n -i {} -c:v libx264 '" + temp_filename + "'"
            },
            {
                'key': 'ExecAfterDownload',
                'exec_cmd': "if [[ $(ls -l {} | cut -d' ' -f8) -ge $(ls -l '" + temp_filename + "' | cut -d' ' -f8) ]]; then echo 'Moving file'; mv '" + temp_filename + "' {}; else echo 'Removing file'; rm '" + temp_filename + "'; fi"
            }
        ]
        if self.execute:
            with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                if ydl.download([url]) == 0:
                    return True
                else:
                    return False
        else:
            self.logger.debug("NOT EXECUTING:\n\turl: {0}\n\tfilename: {1}".format(url, filename))

    def get_filename(self, show_title, season_number, episode_string):
        """
        TODO: fix issue with file always being compressed because it always runs
        maybe a filename to download as, which will be compressed into the final filename, then deleted
        will need to check if a file with the final filename exists and not run for those
        """
        return "{0}/{1}/Season {2}/{1} - {3}{4}".format(self.base_dir, show_title, season_number, episode_string,
                                                        self.extension)

    def add_to_errors(self, error):
        """
        Add error provided to list of errors
        :param error:
        """
        self.logger.error(error)
        self.logger.reset_prefix()

    def add_to_downloaded(self, filename):
        """
        Add filename provided to list of files downloaded
        :param filename:
        """
        self.downloaded.append(filename)

    def print_summary(self):
        """
        Print a summary of the process execution
        """
        print("\n### Execution Summary ###")

        if len(self.downloaded) > 0:
            print("\t[+] {0} episodes downloaded".format(len(self.downloaded)))
            for downloaded in self.downloaded:
                print("\t\t{0}".format(downloaded))

        errors = self.logger.get_logs_by_type("ERROR")
        if len(errors) > 0:
            print("\t[-] {0} errors encountered during execution".format(len(errors)))
            for error in errors:
                print("\t\t{0}".format(error))
