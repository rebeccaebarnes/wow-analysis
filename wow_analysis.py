import pandas as pd
import numpy as np
import json
import os
import requests

GUILD_INFO = {
              'guild_name': 'Last%20Pull',
              'realm': 'Cenarius',
              'region': 'US'
}

def get_logs(api_key, guild_info, log_start=0):
    '''
    Extracts log information from World of Warcraft guild from Warcraft logs
    API from log_start onwards.

    args:
        api_key: (str) Public Key from personal Warcraft Logs account.
        guild_info: dict of guild info with three keys 'guild_name', 'realm',
            'region'.
        log_start: optional. (int) unix time stamp for log start date.
    returns:
        pandas DataFrame.
    '''
    # Gather all guild logs
    link = "https://www.warcraftlogs.com:443/v1/reports/guild/" +  \
        guild_info['guild_name'] + "/" + guild_info['realm'] + "/" + \
        guild_info['region'] + "?api_key="
    guild_logs = requests.get(link + api_key)
    log_list = guild_logs.json()

    # Convert to def
    log_info = pd.DataFrame(log_list, columns = ['id',
                                                 'title',
                                                 'owner',
                                                 'start',
                                                 'end',
                                                 'zone'])
    log_info.columns = ['log_id',
                        'title',
                        'owner',
                        'log_start',
                        'log_end',
                        'zone']
    log_info.drop(['title', 'owner', 'zone'], axis=1, inplace=True)
    log_info = log_info[log_info.log_start >= log_start]

    return log_info

def save_logs(log_info, api_key, guild_info, log_start=0):
    '''
    Saves log information for World of Warcraft guild from Warcraft logs
    API, starting at log_start. Saves log details in json files.

    args:
        log_info: pandas DataFrame obtained from get_logs
        api_key: (str) Public Key from personal Warcraft Logs account.
        guild_info: dict of guild info with three keys 'guild_name', 'realm',
            'region'.
        log_start: optional. (int) unix time stamp for log start date.
    returns:
        None.
    '''
    # Get log details
    log_info = get_logs(api_key, guild_info, log_start)

    # Create folder if doesn't exist
    folder_name = 'log_details'
    if not os.path.exists(folder_name):
        os.makedirs(folder_name)
    # Create files for all log info
    for log_id in log_info.log_id:
        # Check if file exists (limit # requests made)
        file_name = log_id + '_log_details.txt'
        file_path = folder_name + "/" + file_name
        if not os.path.exists(file_path):
            print("Creating file", log_id)
            link = "https://www.warcraftlogs.com:443/v1/report/fights/" \
                + log_id + "?api_key="
            log = requests.get(link + api_key)
            log = log.json()
            data = {}
            for key in ['fights', 'friendlies', 'enemies']:
                data[key] = []
                for entry in log[key]:
                    data[key].append(entry)
            with open(os.path.join(folder_name, file_name), "w") as file:
                json.dump(data, file)

    print("\nAll files created.\n")

def extract_fights():
    '''
    Extracts fight and player info from files in log_details.

    args:
        None.
    returns:
        pandas DataFrame.
    '''
    # Create empty df
    df = pd.DataFrame([], columns = ['log_id',
                                     'pull_id',
                                     'start_time',
                                     'end_time',
                                     'boss_id',
                                     'boss_name',
                                     'difficulty',
                                     'kill',
                                     'player_name'])

    # Read through all the files and create a fight info summary df
    for file in os.listdir('log_details'):
        with open(file) as json_file:
            data = json.load(json_file)

        # Collect fight info
        df_list = []
        try:
            for fight in data['fights']:
                #print(fight['difficulty'])
                #break
                df_list.append({
                    'log_id': log_id,
                    'pull_id': fight['id'],
                    'pull_start': fight['start_time'],
                    'pull_end': fight['end_time'],
                    'boss_id': fight['boss'],
                    'boss_name': fight['name'],
                    'difficulty': fight['difficulty'],
                    'kill': fight['kill']
                })
        except KeyError:
            df_list.append({
                    'log_id': log_id,
                    'pull_id': fight['id'],
                    'pull_start': fight['start_time'],
                    'pull_end': fight['end_time'],
                    'boss_id': fight['boss'],
                    'boss_name': fight['name'],
                    'difficulty': 'non-boss fight',
                    'kill': 'non-boss fight'
                })

        # Convert to df
        fight_data = pd.DataFrame(df_list, columns = ['log_id',
                                                      'pull_id',
                                                      'pull_start',
                                                      'pull_end',
                                                      'boss_id',
                                                      'boss_name',
                                                      'difficulty',
                                                      'kill'])

        # Collect players for each attempt
        df_list = []
        for player in data['friendlies']:
            if player['type'] not in ['NPC', 'Pet']:
                for fight in player['fights']:
                    df_list.append({
                        'pull_id': fight['id'],
                        'player_name': player['name']
                    })
        # Convert to df
        player_data = pd.DataFrame(df_list, columns = ['pull_id', 'player_name'])

        # Merge df's
        merged_df = fight_data.merge(player_data, how='left', on='pull_id')

        # Add on to df
        df = pd.concat([df, merged_df])
        print("Log ID", log_id, "done.")
    print("\nDataframe created.")

    # Clean df
    # Ensure only desired bosses
    df = df[df.boss_name.isin(boss_list)]
    # Get mythic difficulty
    df = df.query('difficulty == 5')
    # Remove unwanted players
    df = df[~(df.player_name.isin(unwanted_players))]
    # Change kill to bool
    df.kill = df.kill.astype('bool')
    # Change start_time and end_time to int
    df.pull_start = df.pull_start.astype('int')
    df.pull_end = df.pull_end.astype('int')
    # Drop difficulty column
    df.drop('difficulty', axis=1, inplace=True)
    print("\nDataframe cleaned.")

    return df



def create_master_list(log_info, fight_info, boss_list, unwanted_players=[]):
    '''
    Creates master list of log, fight and player info and saves in
    'master_list.csv'.

    args:
        log_info: pandas DataFrame obtained from get_logs function.
        fight_info: pandas DataFrame obtained from extract_fights function.
        boss_list: list of strings of boss names, as recorded by Warcraft Logs.
        unwanted_players: optional. list of player names to exclude.
    returns:
        None.
    '''

    # Merge log_info and df
    df = fight_info.merge(log_info, how="left", on="log_id")
    print("\nMaster dataframe created.")

    # Re-order df
    cols = ['log_id',
            'log_start',
            'log_end',
            'pull_id',
            'pull_start',
            'pull_end',
            'boss_id',
            'boss_name',
            'kill',
            'player_name']
    df = df[cols]

    # Read into csv
    df.to_csv('master_list.csv', index=False, encoding='iso-8859-1')
    print("\nmaster_list saved.")

def extract_log_info(api_key,
                     guild_info,
                     boss_list,
                     log_start=0,
                     unwanted_players=[]):
    # Create df of log info
    log_info = get_logs(api_key, guild_info, log_start)

    # Create file for each log's data
    save_logs(log_info, api_key, guild_info, log_start)

    # Extract fight information
    fight_df = extract_fights()

    create_master_list(log_info, fight_df, boss_list, unwanted_players)

def import_clean_master_list():
    '''
    Imports data from 'master_list.csv' as created by get_log_master_list function.
    Reformats data for further analysis.

    args:
        None
    returns:
        pandas DataFrame
    '''
    # Read in master_list
    df = pd.read_csv('master_list.csv', encoding='iso-8859-1')

    # Convert id's to strings
    df.log_id = df.log_id.astype('str')
    df.pull_id = df.pull_id.astype('str')
    df.boss_id = df.boss_id.astype('str')

    # Add columns for log start and end dates
    df['log_date'] = pd.to_datetime(df.log_start, unit='ms')
    df.log_date = df.log_date.dt.date

    # Add columns for pull start and end times
    df['pull_start_time'] = pd.to_datetime(df.pull_start, unit='ms')
    df.pull_start_time = df.pull_start_time.dt.time
    df['pull_end_time'] = pd.to_datetime(df.pull_end, unit='ms')
    df.pull_end_time = df.pull_end_time.dt.time

    # Re-order columns
    cols = ['log_id',
            'log_start',
            'log_end',
            'log_date',
            'pull_id',
            'pull_start',
            'pull_end',
            'pull_start_time',
            'pull_end_time',
            'boss_id',
            'boss_name',
            'kill',
            'player_name']
    df = df[cols]

    return df

def player_info_query(player_name, guild_info, metric, partition=0):
    '''
    Queries Warcraft Logs api for player rankings from guild info according to
    the metric and manages paramaters if applicable. Saves json file of query data.

    args:
        player_name: (str) player name
        guild_info: dict of guild info with three keys 'guild_name', 'realm',
            'region'.
        metric: (str) one of 'hps', 'dps', 'tankhps'
        partition: optional. (int) include if wanting to extract partition other
            than default indicated by Warcraft Logs api.
    returns:
        None.
    '''
    # Create folder if doesn't exist:
    folder_name = 'player_rankings'
    if not os.path.exists(folder_name):
        os.makedirs(folder_name)

    # Manage players not in guild
    try:
        # Create player ranking file
        file_name = player_name + '_' + metric + '_player_rankings.txt'
        file_path = os.path.join(folder_name, file_name)
        print("Creating file for", player_name, "for", metric)
        if partition == 0:
            link = "https://www.warcraftlogs.com:443/v1/rankings/character/" + \
            player_name + "/" + guild_info['realm'] + "/" + \
            guild_info['region'] + "?metric=" + metric + \
            "&timeframe=historical&api_key="
        else:
            link = "https://www.warcraftlogs.com:443/v1/rankings/character/" + \
            player_name + "/" + guild_info['realm'] + "/" + \
            guild_info['region'] + "?metric=" + metric + "&partition=" + \
            str(partition) + "&timeframe=historical&api_key="
        player_info = requests.get(link + api_key)
        player_info = player_info.json()
        with open(file_path, "w") as file:
            json.dump(player_info, file)
    except TypeError:
        print("Missed data for", player, ": not in guild")

def import_player_info(player_names):
    '''
    Queries Warcraft Logs api for players' rankings for hps, dps and tankhps.
    Saves json file of query data.

    args:
        player_name: (str) player name
        metric: (str) one of 'hps', 'dps', 'tankhps'
    returns:
        None
    '''
    metrics = ['hps', 'dps', 'tankhps']

    for player in player_names:
        for metric in metrics:
            player_info_query(player, metric)

def player_rankings_df(player_name, metric, primary_role):
    '''
    Creates df of player rankings for metric.

    args:
        player_name: (str) player name
        metric: (str) one of 'hps', 'dps', 'tankhps'
        primary_role: (str) one of 'healer', 'damage', 'tank'
    returns:
        pandas DataFrame
    '''
    # Manage players not in guild
    try:
        # Open file
        file_name = 'player_rankings/' + player_name + '_' + metric + '_player_rankings.txt'
        with open(file_name) as json_file:
            data = json.load(json_file)

        # Create player df
        df_list = []
        for boss in data:
            # Only gather mythic difficulty
            if boss['difficulty'] == 5:
                df_list.append({
                    'player_name': player_name,
                    'primary_role': primary_role,
                    'boss_id': boss['encounterID'],
                    'boss_name': boss['encounterName'],
                    'percentile': boss['percentile'],
                    'ilevel': boss['ilvlKeyOrPatch'],
                    'spec': boss['spec'],
                    'metric': metric,
                    'ranking_date': boss['startTime']
                })

    except TypeError:
        print("Missed data for", player_name, ": not in guild")

    # Convert to df
    player_data = pd.DataFrame(df_list, columns=['player_name',
                                                 'primary_role',
                                                 'boss_id',
                                                 'boss_name',
                                                 'percentile',
                                                 'ilevel',
                                                 'spec',
                                                 'metric',
                                                 'ranking_date'])

    return player_data

def player_rankings():
    '''
    Creates df of players' rankings from 'player_list.csv', reads info from
    player files and saves in 'player_rankings.csv'.

    args:
        player_name: (str) player name
        metric: (str) one of 'hps', 'dps', 'tankhps'
        primary_role: (str) one of 'healer', 'damage', 'tank'
    returns:
        pandas DataFrame
    '''
    # Read in player_list
    player_list = pd.read_csv('player_list.csv', encoding='iso-8859-1')
    player_names = list(player_list.player)
    metrics = ['hps', 'dps', 'tankhps']

    # Create empty df
    df = pd.DataFrame([], columns=['player_name',
                                   'primary_role',
                                   'boss_id',
                                   'boss_name',
                                   'percentile',
                                   'ilevel',
                                   'spec',
                                   'metric',
                                   'ranking_date'])

    # Read in player info
    for player in player_names:
        for metric in metrics:
            # Create player df
            player_df = player_rankings_df(player, metric, player_list[player_list.player == player]['primary_role'].iloc[0])
            # Join to df
            df = pd.concat([df, player_df])

    # Clean df
    df.percentile = df.percentile.astype('int')
    df.ilevel = df.ilevel.astype('int')

    # Save df
    df.to_csv('player_rankings.csv', index=False, encoding='iso-8859-1')

    return df
