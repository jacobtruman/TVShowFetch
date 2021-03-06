import requests
import os
import time


def request_data(args):
    """
    Request data from url
    :param args:
    :return: data from url
    """
    sleep_time = 5
    max_retries = 5
    if 'logger' in args:
        logger = args['logger']
    else:
        logger = None

    if 'url' not in args:
        if logger is not None:
            logger.error("No url provided")
        return False

    if 'headers' not in args:
        args['headers'] = {}

    if 'method' not in args:
        args['method'] = "get"

    if args['method'] == 'post':
        if 'data' not in args:
            args['data'] = {}
        response = requests.post(args['url'], headers=args['headers'], json=args['data'])
    else:
        if 'params' not in args:
            args['params'] = {}
        response = requests.get(args['url'], headers=args['headers'], params=args['params'])

    if response.status_code == 200:
        return response
    else:
        if 'try' not in args:
            args['try'] = 0
        args['try'] += 1
        if args['try'] >= max_retries:
            if logger is not None:
                logger.error(
                    "Something went wrong: '{0}' returned status code {1}".format(args['url'], response.status_code))
            return False
        else:
            if logger is not None:
                logger.warning(
                    "Something went wrong: '{0}' returned status code {1}. Sleeping {2} seconds and trying again".format(args['url'], response.status_code, sleep_time))
            time.sleep(sleep_time)
            return request_data(args)


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
    to_replace[u"\u2019"] = ""
    to_replace[u"\xf1"] = "n"
    to_replace['"'] = ""
    to_replace['!'] = ""
    to_replace[','] = ""
    to_replace['.'] = ""
    to_replace[' - '] = " "
    to_replace['-'] = " "
    to_replace[':'] = ""
    to_replace['?'] = ""

    # replace custom replacements
    for search, replace in to_replace.iteritems():
        search = search.lower()
        if search in string:
            string = string.replace(search, replace.lower())

    # strip off leading "the "
    if string.lower().startswith("the "):
        string = string[4:None]

    # strip off leading "a "
    if string.lower().startswith("a "):
        string = string[2:None]

    return string.strip()


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
