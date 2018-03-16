import os.path
import sys
import requests
import json
import inspect
import logger
import datetime
import time
import urllib

from bs4 import BeautifulSoup
from os.path import expanduser
from subprocess import Popen, PIPE


class TVShowFetch:

    def __init__(self, args=None):
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

    def get_ffmpeg(self):
        if self.ffmpeg is None:
            self.ffmpeg = self.run_command("which ffmpeg", True)

        return self.ffmpeg

    def process_config(self, config):
        """
        Process the config provided
        :param config:
        """
        method = "get_{0}_show".format(config['network'].lower().replace(" ", "_"))
        if hasattr(self, method):
            shows = self.get_active_shows(config['shows'])
            count = len(shows)
            if count > 0:
                num = 0
                for show_info in shows:
                    num += 1
                    self.logger.add_to_log(
                        "Processing show {0} / {1} :: '{2}'".format(num, count, show_info['show_title']))
                    getattr(self, method)(show_info)
        else:
            self.add_to_errors("'{0}' does not exist".format(method))

    def get_cbs_show(self, show_info):
        """
        Get CBS show provided
        :param config:
        """
        base_url = "https://www.cbs.com"
        offset = 0
        limit = 100
        show_title = show_info['show_title']

        if 'single_season' in show_info and show_info['single_season']:
            show_url = "{0}/carousels/videosBySection/{1}/offset/{2}/limit/{3}/xs/0/".format(base_url,
                                                                                             show_info[
                                                                                                 'show_id'],
                                                                                             offset, limit)
        else:
            show_url = "{0}/carousels/shows/{1}/offset/{2}/limit/{3}/".format(base_url, show_info['show_id'],
                                                                              offset,
                                                                              limit)

        response = self.request_data({"url": show_url})
        if response is not False:
            json_obj = json.loads(response.text)

            episode_data = {'show': show_title, 'episodes': {}}

            if 'result' in json_obj and 'data' in json_obj['result']:
                for record in json_obj['result']['data']:
                    skip = False
                    season_number = record['season_number']
                    episode_number = record['episode_number']
                    episode_url = "{0}{1}".format(base_url, record['url'])
                    filename = None

                    if ',' in episode_number:
                        episode_numbers = episode_number.split(",")
                        eps = []
                        first_episode_number = None
                        last_episode_number = None
                        for episode_number in episode_numbers:
                            this_episode_number = episode_number.trim()
                            if first_episode_number is None:
                                first_episode_number = this_episode_number

                            if last_episode_number is not None and (
                                    this_episode_number - last_episode_number) != 1:
                                self.logger.set_prefix("[ {0} ][ {1} ]".format(show_title, season_number))
                                self.add_to_errors(
                                    "Non-sequential episodes ({0} - {1}) - skipping".format(last_episode_number,
                                                                                            this_episode_number))
                                skip = True
                                break

                            last_episode_number = this_episode_number

                        if skip:
                            continue

                        eps.append(first_episode_number.zfill(2))
                        eps.append(last_episode_number.zfill(2))

                        episode_string = '-'.join(eps)
                        filename = "{0}/%(series)s/Season %(season_number)s/%(series)s - S%(season_number)02d{1}".format(
                            self.base_dir, episode_string)

                    if season_number not in episode_data['episodes']:
                        episode_data['episodes'][season_number] = {}
                    if episode_number not in episode_data['episodes'][season_number]:
                        episode_data['episodes'][season_number][episode_number] = {}

                    episode_data['episodes'][season_number][episode_number]['url'] = episode_url
                    episode_data['episodes'][season_number][episode_number]['filename'] = filename

            self.process_episodes(episode_data)

    def get_abc_show(self, show_info):
        """
        Process ABC show provided
        :param show_info:
        """
        base_url = "http://abc.go.com"
        show_title = show_info['show_title']
        show_url = "{0}/shows/{1}/episode-guide/".format(base_url, show_info['show_id'])

        response = self.request_data({"url": show_url})
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
                        contents = self.request_data({"url": "{0}{1}".format(base_url, season_url)})
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

                                        if season_number not in episode_data['episodes']:
                                            episode_data['episodes'][season_number] = {}
                                        if episode_number not in episode_data['episodes'][season_number]:
                                            episode_data['episodes'][season_number][episode_number] = {
                                                'filename': None}

                                        episode_url = "{0}{1}".format(base_url,
                                                                      season_div.attrs['data-url']).strip()
                                        episode_data['episodes'][season_number][episode_number][
                                            'url'] = episode_url

            self.process_episodes(episode_data)

    def get_nbc_show(self, show_info):
        """
        Process NBC show provided
        :param show_info:
        """
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

            response = self.request_data({"url": show_url})
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

                            filename = "{0}/{1}/Season {2}/{1} - {3}".format(
                                self.base_dir, show_title, season_number, episode_string)

                            if season_number not in episode_data['episodes']:
                                episode_data['episodes'][season_number] = {}
                            if episode_number not in episode_data['episodes'][season_number]:
                                episode_data['episodes'][season_number][episode_number] = {}

                            episode_data['episodes'][season_number][episode_number]['url'] = attributes[
                                'permalink']
                            episode_data['episodes'][season_number][episode_number]['filename'] = filename

                self.process_episodes(episode_data)

    def get_active_shows(self, shows):
        """
        Get active shows from config provided
        :param shows:
        :return: List of active show configs
        """
        active_shows = []
        for show_info in shows:
            if 'active' not in show_info or show_info['active'] is False:
                self.logger.add_to_log(
                    "{0} is not active - skipping".format(show_info['show_title']))
            elif self.title_filter is not None and self.title_filter not in show_info['show_title']:
                self.logger.add_to_log(
                    "{0} does not match filter provided: '{1}' - skipping".format(
                        show_info['show_title'],
                        self.title_filter))
            else:
                active_shows.append(show_info)

        self.logger.add_to_log("Shows to be processed: {0}".format(len(active_shows)))

        return active_shows

    def request_data(self, args=None):
        """
        Request data from url
        :param args:
        :return: data from url
        """
        if 'url' not in args:
            self.logger.add_to_log("No url provided", "ERROR")
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
            self.logger.add_to_log(
                "Something went wrong: '{0}' returned status code {1}".format(args['url'], response.status_code),
                "ERROR")
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
                self.logger.add_to_log("Processing latest episode")
                if latest is not False:
                    max_season, max_episode = latest
                    self.logger.set_prefix("\t[ {0} ][ Season {1} ][ Episode {2} ]".format(show_title, max_season,
                                                                                           max_episode))
                    latest_episode = episodes[max_season][max_episode]
                    self.logger.add_to_log("")
                    self.process_url(latest_episode['url'], latest_episode['filename'])
                else:
                    self.logger.add_to_log("[ {0} ] Unable to get the latest episode".format(show_title))
            else:
                self.logger.add_to_log("Processing episodes from {0} seasons".format(len(episodes)))
                season_numbers = episodes.keys()
                season_numbers.sort(key=int)
                for season_num in season_numbers:
                    episode_numbers = episodes[season_num].keys()
                    episode_numbers.sort(key=int)
                    self.logger.set_prefix("\t[ {0} ][ Season {1} ]".format(show_title, season_num))
                    self.logger.add_to_log("Processing {0} episodes".format(len(episode_numbers)))
                    for episode_num in episode_numbers:
                        episode = episodes[season_num][episode_num]
                        self.logger.set_prefix("\t[ {0} ][ Season {1} ][ Episode {2} ]".format(show_title, season_num,
                                                                                               episode_num))
                        self.logger.add_to_log("")
                        self.process_url(episode['url'], episode['filename'])
        else:
            self.logger.add_to_log("Episode data structure provided is missing required data")

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

    def process_url(self, url, filename=None):
        """
        Process show url provided
        :param url:
        :param filename:
        :return: Boolean
        """
        self.logger.add_to_log("Filename passed in: {0}".format(filename))
        filename_auto = self.get_filename(url)
        if filename_auto is not False:
            self.logger.add_to_log("Filename discovered: {0}".format(filename_auto))

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
            self.logger.add_to_log("File already exists: {0}".format(new_filename))
        elif new_filename is None and os.path.exists(filename):
            self.logger.add_to_log("File already exists: {0}".format(filename))
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
                self.logger.add_to_log("NOT EXECUTING COMMAND: {0}".format(cmd))

        return True

    def get_filename(self, url):
        """
        Get filename of the show url provided via the youtube-dl script
        :param url:
        :return: filename of show
        """
        cmd = "{0} --get-filename {1}".format(self.get_fetch_command(), url)
        self.logger.add_to_log("{0}".format(cmd))

        return self.run_command(cmd, True)

    def run_command(self, cmd, output=False):
        """
        Run command provided
        :param cmd:
        :param output:
        :return: output of command
        """
        ret = True

        self.logger.add_to_log("Running command: {0}".format(cmd))

        p = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE)
        out, err = p.communicate()
        status = p.returncode

        if self.verbose:
            if len(out.rstrip()) > 0:
                self.logger.add_to_log(out.rstrip(), "DEBUG")
            if len(err.rstrip()) > 0:
                self.logger.add_to_log(err.rstrip(), "ERROR")

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
                self.logger.add_to_log("Deleting source file '{0}'".format(filename))
                os.remove(filename)
                if rename:
                    os.rename(new_filename, filename)
            else:
                self.logger.add_to_log(
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
        self.logger.add_to_log(error, "ERROR")
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
