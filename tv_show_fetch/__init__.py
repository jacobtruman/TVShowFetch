import os.path
import requests
import inspect
import logger
import youtube_dl

import sys

from os.path import expanduser
from subprocess import Popen, PIPE
from fetchers import *


class TVShowFetch:

    def __init__(self, args=None):
        """
        Class to fetch TV shows from network websites
        :param args:
        """
        if args is None:
            args = {}

        self.home_dir = expanduser("~")
        self.base_dir = '{0}/TVShows'.format(self.home_dir)
        self.title_filter = ""
        self.latest = True
        self.verbose = True
        self.execute = True

        # override any default settings defined in params
        if args is not None:
            for arg in args:
                self.__dict__[arg] = arg[arg]

        self.logger = logger.Logger({'colorize': True})
        self.downloaded = []
        self.extension = ".mp4"
        self.ffmpeg = None

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

    def get_ffmpeg(self):
        if self.ffmpeg is None:
            self.ffmpeg = self.run_command("which ffmpeg", True)

        return self.ffmpeg

    def process_config(self, config):
        """
        Process the config provided
        :param config:
        """
        module_name = "fetchers.{0}".format(config['network'].lower())
        if module_name in sys.modules:
            method = "get_show"
            module = getattr(sys.modules[module_name], config['network'])(self)
            if hasattr(module, method):
                shows = self.get_active_shows(config['shows'])
                count = len(shows)
                if count > 0:
                    num = 0
                    for show_info in shows:
                        num += 1
                        self.logger.info(
                            "Processing show {0} / {1} :: '{2}'".format(num, count, show_info['show_title']))
                        if show_info['show_title'] == "The Good Place":
                            getattr(module, method)(show_info)
            else:
                self.add_to_errors(
                    "Module '{0}' does not have method '{1}'".format(module_name, method))
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
        """
        Request data from url
        :param args:
        :return: data from url
        """
        if 'url' not in args:
            self.logger.error("No url provided")
            return False

        if 'headers' not in args:
            args['headers'] = {}

        if 'method' not in args:
            args['method'] = "get"

        if args['method'] == 'post':
            response = requests.post(args['url'], headers=args['headers'])
        else:
            response = requests.get(args['url'], headers=args['headers'])

        if response.status_code == 200:
            return response
        else:
            self.logger.error(
                "Something went wrong: '{0}' returned status code {1}".format(args['url'], response.status_code))
            return False

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

            self.logger.set_prefix(None)

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

    def process_url_OLD(self, url, filename=None):
        """
        Process show url provided
        :param url:
        :param filename:
        :return: Boolean
        """
        self.logger.info("Filename passed in: {0}".format(filename))
        filename_auto = self.get_filename_OLD(url)
        if filename_auto is not False:
            self.logger.info("Filename discovered: {0}".format(filename_auto))

        cmd = self.get_fetch_command()

        if filename is not None:
            cmd += " -o '{0}.%(ext)s'".format(filename)
        elif filename_auto:
            filename = filename_auto
        else:
            self.add_to_errors("Unable to process url: {0}".format(url))
            return False

        file_info = self.get_file_info(filename)

        cmd = "{0} {1}".format(cmd, url)

        new_filename = None
        if file_info['extension'] != self.extension:
            new_filename = filename.replace(file_info['extension'], self.extension)

        if new_filename is not None and os.path.exists(new_filename):
            self.logger.info("File already exists: {0}".format(new_filename))
        elif new_filename is None and os.path.exists(filename):
            self.logger.info("File already exists: {0}".format(filename))
        else:
            if self.execute:
                if self.run_command(cmd):
                    self.convert(filename, new_filename)
                    if new_filename is None:
                        downloaded = new_filename
                    else:
                        downloaded = filename
                    self.add_to_downloaded(downloaded)
            else:
                self.logger.debug("NOT EXECUTING COMMAND: {0}".format(cmd))

        return True

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
            self.logger.debug("NOT EXECUTING:\nurl: {0}\nfilename: {1}".format(url, filename))

    def get_filename_OLD(self, url):
        """
        Get filename of the show url provided via the youtube-dl script
        :param url:
        :return: filename of show
        """
        cmd = "{0} --get-filename {1}".format(self.get_fetch_command(), url)
        self.logger.info("{0}".format(cmd))

        return self.run_command(cmd, True)

    def get_filename(self, show_title, season_number, episode_string):
        return "{0}/{1}/Season {2}/{1} - {3}{4}".format(self.base_dir, show_title, season_number, episode_string,
                                                        self.extension)

    def run_command(self, cmd, output=False):
        """
        Run command provided
        :param cmd:
        :param output:
        :return: output of command
        """
        ret = True

        self.logger.info("Running command: {0}".format(cmd))

        p = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE)
        out, err = p.communicate()
        status = p.returncode

        if self.verbose:
            if len(out.rstrip()) > 0:
                self.logger.debug(out.rstrip())
            if len(err.rstrip()) > 0:
                self.logger.error(err.rstrip())

        if status != 0:
            self.logger.set_prefix("[ In {0} ]".format(inspect.stack()[0][3]))
            self.add_to_errors("the command '{0}' exited with code '{1}': {2}".format(cmd, status, err.rstrip()))
            ret = False
        else:
            if output:
                ret = out.rstrip()

        return ret

    def convert(self, filename=None, new_filename=None):
        """
        Convert file provided
        :param filename:
        :param new_filename:
        """
        if filename is not None:
            rename = False
            file_info = self.get_file_info(filename)

            if new_filename is None or file_info['extension'] == self.extension:
                new_filename = filename.replace(file_info['extension'], "NEW{0}".format(self.extension))
                rename = True

            cmd = "{0} -i '{1}' -c:v libx264 '{2}'".format(self.get_ffmpeg(), filename, new_filename)
            if self.run_command(cmd):
                self.logger.info("Deleting source file '{0}'".format(filename))
                os.remove(filename)
                if rename:
                    os.rename(new_filename, filename)
            else:
                self.logger.info(
                    "Conversion failed; keeping source file '{0}'".format(filename))
        else:
            self.add_to_errors("Filename cannot be empty")

    def get_fetch_command(self):
        """
        Get the youtube-dl command to be used to fetch the show
        :return: fetch command
        """
        return "youtube-dl --no-mtime --audio-quality 0 --no-check-certificate -o '{0}/%(series)s/Season %(season_number)s/%(series)s - S%(season_number)02dE%(episode_number)02d.%(ext)s'".format(
            self.base_dir)

    def add_to_errors(self, error):
        """
        Add error provided to list of errors
        :param error:
        """
        self.logger.error(error)
        self.logger.set_prefix(None)

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

    @staticmethod
    def sanitize_string(string, to_replace=None):
        """
        Sanitize string for comparison purposes
        :param string:
        :param to_replace:
        :return: sanitized string
        """
        if to_replace is None:
            to_replace = {}
        string = string.strip().lower()
        to_replace[' & '] = " and "
        to_replace["'"] = ""
        to_replace['"'] = ""
        to_replace['!'] = ""
        to_replace[','] = ""

        # strip off leading "the "
        if string.startswith("the "):
            string = string[4:None]

        # strip off leading "a "
        if string.startswith("a "):
            string = string[2:None]

        # replace custom replacements
        for search, replace in to_replace.iteritems():
            if search in string:
                string = string.replace(search.lower(), replace.lower())

        return string.strip()

    @staticmethod
    def get_file_info(file_path):
        """
        Get infor for file path provided
        :param file_path:
        :return: dictionary of file information
        """
        absolute_path = os.path.abspath(file_path)
        dirname = os.path.dirname(absolute_path)
        basename = os.path.basename(absolute_path)
        extension = os.path.splitext(absolute_path)[-1]

        return {'absolute_path': absolute_path, 'dirname': dirname, 'basename': basename, 'extension': extension}
