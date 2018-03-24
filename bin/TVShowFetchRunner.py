import os.path
import json
import glob
import tv_show_fetch
import argparse
import atexit
import sys

from os.path import expanduser


def parse_args():
    """
    Parse command line arguments.
    """
    parser = argparse.ArgumentParser(
        description='Run TV Show Fetch functions.',
    )

    parser.add_argument(
        '-e', '--execute',
        action='store_true',
        dest='execute',
        help='Execute downloads (not dry run)',
    )

    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        dest='verbose',
        help='Enable verbose logging',
    )

    parser.add_argument(
        '-l', '--latest',
        action='store_true',
        dest='latest',
        help='Get only the latest episode available',
    )

    parser.add_argument(
        '-a', '--all',
        action='store_true',
        dest='all',
        help='Get all episodes available',
    )

    parser.add_argument(
        '-f', '--filter',
        default=None,
        dest='filter',
        help='Filter by show name',
    )

    parser.add_argument(
        '-n', '--network',
        default=None,
        dest='network',
        help='Network for which to run',
    )

    parser.add_argument(
        '-c', '--configs_dir',
        default=None,
        dest='configs_dir',
        help='Directory containing the config files',
    )

    """
    subparsers = parser.add_subparsers(title='commands')

    # sub parser definition
    my_sub_parser = subparsers.add_parser(
        'my-sub-parsers-name',
        help='Some useful help',
    )
    my_sub_parser.add_argument(
        '-x', '--x_param',
        default=None,
        dest='x_param',
        help='Info for this param',
    )
    my_sub_parser.set_defaults(
        func=my_function,
    )
    """

    args = parser.parse_args()
    return args


def get_all_config_files(configs_dir):
    if configs_dir is not None and os.path.exists(configs_dir):
        configs = glob.glob("{0}/*.json".format(configs_dir))
    else:
        configs = []

    return configs


def fail(msg):
    print('FAILURE: {0}'.format(msg))
    sys.exit(0)


def cleanup(args):
    if 'lock_file' in args:
        os.remove(args['lock_file'])
        msg = 'Lock file removed: {0}'.format(args['lock_file'])
        if 'logger' in args:
            args['logger'].info(msg)
        else:
            print(msg)


def main():
    """
    Main function.
    """
    args = parse_args()

    home_dir = expanduser("~")

    if args.configs_dir is not None:
        configs_dir = args.configs_dir
    else:
        configs_dir = '~/tvshow_configs'

    if configs_dir[:1] == '~':
        configs_dir = configs_dir.replace('~', home_dir)

    if not os.path.exists(configs_dir):
        fail("Configs directory provided does not exist: {0}".format(configs_dir))

    base_config = {}
    base_config_file = '{0}/config.json'.format(configs_dir)
    if os.path.exists(base_config_file):
        try:
            base_config = json.loads(open(base_config_file, "r").read())
        except ValueError, e:
            fail(e.message)

    if 'base_dir' in base_config:
        base_dir = base_config['base_dir']
    else:
        base_dir = '~/TVShows'

    if base_dir[:1] == '~':
        base_dir = base_dir.replace('~', home_dir)

    if not os.path.exists(base_dir):
        fail("Base directory provided does not exist: {0}".format(base_dir))

    fetch_args = {'base_config': base_config, 'base_dir': base_dir}

    if 'log_dir' in base_config:
        log_dir = base_config['log_dir']
        if log_dir[:1] == '~':
            log_dir = log_dir.replace('~', home_dir)
        fetch_args['log_dir'] = log_dir

    if args.network is not None:
        network_filename = '{0}/{1}.json'.format(configs_dir, args.network.lower())
        if not os.path.exists(network_filename):
            fail_msg = "Invalid network provided ({0}); config file does not exist: {1}".format(args.network, network_filename)
            networks = [
                config_file.replace('{0}/'.format(configs_dir), '').replace('.json', '')
                for config_file in get_all_config_files(configs_dir)
            ]
            fail_msg += "\n\tAvailable networks: {0}".format(networks)
            fail(fail_msg)
        else:
            config_files = [network_filename]
    else:
        config_files = get_all_config_files(configs_dir)

    if args.filter is not None:
        fetch_args['title_filter'] = args.filter.lower()

    # only add latest if it is not the default (false)
    if args.latest:
        fetch_args['latest'] = args.latest
    # only add all if it is not the default (false)
    if args.all:
        fetch_args['all'] = args.all

    fetch_args['execute'] = args.execute
    fetch_args['verbose'] = args.verbose

    fetcher = tv_show_fetch.TVShowFetch(fetch_args)

    # check if process is already running
    filename, file_extension = os.path.splitext(os.path.basename(__file__))
    lock_file = '/tmp/{0}.lock'.format(filename)
    if os.path.exists(lock_file):
        fail('Lock file exists: {0}'.format(lock_file))
    else:
        atexit.register(cleanup, args={'lock_file': lock_file, 'logger': fetcher.logger})
        open(lock_file, 'w+')
        fetcher.logger.info('Lock acquired: {0}'.format(lock_file))

    # run requested action
    # args.func(args)

    for config_file in config_files:
        # exclude base config (config.json)
        if config_file != base_config_file:
            try:
                config = json.loads(open(config_file, "r").read())
                fetcher.process_config(config)
            except ValueError, e:
                fail(e.message)

    fetcher.print_summary()


if __name__ == '__main__':
    main()
