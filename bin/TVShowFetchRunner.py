import os.path
import json
import glob
import tv_show_fetch
from tv_show_fetch import thetvdbapi
import sys

from os.path import expanduser

home_dir = expanduser("~")

base_dir = '{0}/TVShows'.format(home_dir)
configs_dir = '{0}/tvshow_configs'.format(home_dir)
config_files = glob.glob("{0}/*.json".format(configs_dir))

base_config = {}
base_config_file = '{0}/config.json'.format(configs_dir)
if os.path.exists(base_config_file):
    try:
        base_config = json.loads(open(base_config_file, "r").read())
    except ValueError, e:
        print(e.message)

fetcher = tv_show_fetch.TVShowFetch({'base_config': base_config})

for config_file in config_files:
    # exclude base config (config.json)
    if config_file != base_config_file:
        try:
            config = json.loads(open(config_file, "r").read())
            network = "NBC"
            if config['network'] == network:
                fetcher.process_config(config)
            else:
                print("Network {0} is not {1} skipping".format(config['network'], network))
            #fetcher.process_config(config)
        except ValueError, e:
            print(e.message)
