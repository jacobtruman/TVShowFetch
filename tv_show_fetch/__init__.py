import os.path
import utils
import thetvdbapi
import youtube_dl
import datetime
import sys
import trulogger

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

        if 'base_dir' not in args:
            raise ValueError('base_dir not provided')

        self.base_dir = None
        self.log_dir = None
        self.title_filter = None
        self.latest = None
        self.all = None
        self.base_config = None
        self.verbose = True
        self.execute = True

        # override any default settings defined in params
        for arg in args:
            self.__dict__[arg] = args[arg]

        logger_config = {'colorize': True, 'verbose': self.verbose}
        if self.log_dir is not None:
            date = datetime.datetime.today().strftime('%Y-%m-%d')
            logger_config['log_file'] = '{0}/TVShowFetch_{1}.log'.format(self.log_dir, date)
        self.logger = trulogger.TruLogger(logger_config)
        self.thetvdbapi = thetvdbapi.TheTVDBApi(self, self.base_config['tvdb'])
        self.downloaded = []
        self.extension = ".mp4"

        self.ydl_opts = {
            'format': self.extension.replace(".", ""),
            'verbose': True,
            'nocheckcertificate': True,
            'progress_hooks': [self.ydl_progress_hook],
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
            self.logger.info('Done downloading, now compressing...')

    def process_config(self, config):
        """
        Process the config provided
        :param config:
        """
        latest = self.latest

        if self.all is None:
            if self.latest is None and 'latest' in config:
                self.latest = config['latest']
            else:
                self.latest = True
        elif self.all:
            self.latest = False

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
                        try:
                            getattr(module, method)(show_info)
                        except Exception as e:
                            self.logger.error(e.message)
                        self.logger.reset_prefix()
            else:
                self.add_to_errors("Module '{0}' does not have method '{1}'".format(module_name, method))
        else:
            self.add_to_errors("Module '{0}' does not exist".format(module_name))

        self.latest = latest

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
            elif self.title_filter is not None and self.title_filter not in show_info['show_title'].lower():
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
                    self.process_url(latest_episode['url'], latest_episode['filenames'])
                else:
                    self.logger.info("[ {0} ] Unable to get the latest episode".format(show_title))
            else:
                self.logger.info("Processing episodes from {0} seasons".format(len(episodes)))
                season_numbers = episodes.keys()
                season_numbers.sort(key=int)
                for season_num in season_numbers:
                    episode_numbers = episodes[season_num].keys()
                    episode_numbers.sort(key=int)
                    self.logger.set_prefix("\t[ {0} ][ Season {1} ]".format(show_title, season_num))
                    self.logger.info("Processing {0} episodes".format(len(episode_numbers)))
                    for episode_num in episode_numbers:
                        episode = episodes[season_num][episode_num]
                        self.logger.set_prefix("\t[ {0} ][ Season {1} ][ Episode {2} ]".format(show_title, season_num,
                                                                                               episode_num))
                        self.process_url(episode['url'], episode['filenames'])
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

    def process_url(self, url, filenames):
        """
        Process show url provided
        :param url:
        :param filenames:
        :return: Boolean
        """
        if not self.file_exists(filenames['final']):
            ydl_opts = self.ydl_opts.copy()
            ydl_opts['outtmpl'] = filenames['downloading']
            ydl_opts['postprocessors'] = [
                {
                    'key': 'ExecAfterDownload',
                    'exec_cmd': "ffmpeg -n -i {} -c:v libx264 '" + filenames['final'] + "'"
                },
                {
                    'key': 'ExecAfterDownload',
                    'exec_cmd': "if [[ $(wc -c '" + filenames[
                        'final'] + "' | awk '{print $1}') -ge $(ls -l {} | awk '{print $1}') ]]; then echo 'Moving file'; mv {} '" +
                                filenames['final'] + "'; else echo 'Removing file'; rm {}; fi"
                }
            ]
            if self.execute:
                with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                    self.logger.info("Downloading episode: {0}".format(filenames['final']))
                    try:
                        ydl.download([url])
                        self.add_to_downloaded(filenames['final'])
                        return True
                    except Exception as e:
                        self.logger.error(
                            "There was a problem downloading episode: {0} -> {1}".format(url, filenames['final']))
                        self.logger.error(e.message)
                        return False
            else:
                self.logger.debug("NOT EXECUTING:\n\turl: {0}\n\tfilename: {1}".format(url, filenames['downloading']))

    def get_episode_string(self, season_number, episode_numbers):
        season = str(season_number).zfill(2)
        episodes = []
        for episode_number in episode_numbers:
            episodes.append(str(episode_number).zfill(2))

        return 'S{0}E{1}'.format(season, '-E'.join(episodes))

    def get_filenames(self, show_title, season_number, episode_string):
        base_filename = '{0}/{1}/Season {2}/{1} - {3}'.format(self.base_dir, show_title, season_number, episode_string)
        files = {
            'downloading': '{0}.DOWNLOAD{1}'.format(base_filename, self.extension),
            'final': '{0}{1}'.format(base_filename, self.extension)
        }
        return files

    def file_exists(self, filename):
        if os.path.exists(filename):
            self.logger.warning("Episode already downloaded: {0}".format(filename))
            return True
        else:
            return False

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
        self.logger.success("Downloaded episode: {0}".format(filename))

    def print_summary(self):
        """
        Print a summary of the process execution
        """
        self.logger.add_to_log("\n### Execution Summary ###")

        if len(self.downloaded) > 0:
            self.logger.add_to_log("\t[+] {0} episodes downloaded".format(len(self.downloaded)))
            for downloaded in self.downloaded:
                self.logger.add_to_log("\t\t{0}".format(downloaded))

        errors = self.logger.get_logs_by_type("ERROR")
        if len(errors) > 0:
            self.logger.add_to_log("\t[-] {0} errors encountered during execution".format(len(errors)))
            for error in errors:
                self.logger.add_to_log("\t\t{0}".format(error))
