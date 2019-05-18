import pandas as pd
import json
import os
import requests

GUILD_INFO = {
              'guild_name': 'Tempest',
              'realm': 'Proudmoore',
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

def get_json_data(folder_name, file):
    '''Obtains json data from specified location.

    args:
        folder_name: (str).
        file: (str).
    returns:
        json data as dict.
    '''
    with open(os.path.join(folder_name, file)) as json_file:
        data = json.load(json_file)

    return data

def create_fight_df(data, file):
    '''Create dataframe of specific fight details from json file.

    args:
        data: json file.
        file: (str) File name.
    returns:
        Pandas DataFrame.
    '''
    # Extract data
    df_list = []
    log_id = file.split('_')[0]
    for fight in data['fights']:
        try:
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
            df_list.append({'log_id': log_id,
                            'pull_id': fight['id'],
                            'pull_start': fight['start_time'],
                            'pull_end': fight['end_time'],
                            'boss_id': fight['boss'],
                            'boss_name': fight['name'],
                            'difficulty': 'non-boss fight',
                            'kill': 'non-boss fight'})

    # Convert to df
    fight_data = pd.DataFrame(df_list, columns=['log_id',
                                                'pull_id',
                                                'pull_start',
                                                'pull_end',
                                                'boss_id',
                                                'boss_name',
                                                'difficulty',
                                                'kill'])

    return fight_data

def create_player_df(data):
    '''Create dataframe of players per fight from json file.

    args:
        data: json file.
    returns:
        Pandas DataFrame.
    '''
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
    player_data = pd.DataFrame(df_list,
                               columns=['pull_id', 'player_name'])
    return player_data

def create_combined_df():
    # Create empty df
    df = pd.DataFrame([], columns=['log_id',
                                   'pull_id',
                                   'pull_start',
                                   'pull_end',
                                   'boss_id',
                                   'boss_name',
                                   'difficulty',
                                   'kill',
                                   'player_name'])

    # Get fight data
    folder_name = 'log_details'
    for file in os.listdir(folder_name):
        if os.path.isfile(os.path.join(folder_name, file)):
            log_id = file.split('_')[0]
            data = get_json_data(folder_name, file)
            fight_df = create_fight_df(data, file)
            player_df = create_player_df(data)
            merged_df = fight_df.merge(player_df, how='left', on='pull_id')
            # Add on to df
            df = pd.concat([df, merged_df])
            print("Log ID", log_id, "done.")
    print("\nDataframe created.")
    return df

def extract_fights(boss_list, unwanted_players=[]):
    '''
    Extracts fight and player info from files in log_details.

    args:
        boss_list: list of instance bosses according to Warcraft Logs.
        unwanted_players: optional. list of players to exclude from extraction.
    returns:
        pandas DataFrame.
    '''
    df = create_combined_df()

    # Clean df
    # Ensure only desired bosses
    df = df[df.boss_name.isin(boss_list)]
    # Get mythic difficulty
    df = df[(df.difficulty == 4) | (df.difficulty == 5)]
    # Remove unwanted players
    df = df[~(df.player_name.isin(unwanted_players))]
    # Change kill to bool
    df.kill = df.kill.astype('bool')
    # Change start_time and end_time to int
    df.pull_start = df.pull_start.astype('int')
    df.pull_end = df.pull_end.astype('int')
    print("\nDataframe cleaned.")

    return df



def create_master_list(log_info, fight_info):
    '''
    Creates master list of log, fight and player info and saves in
    'master_list.csv'.

    args:
        log_info: pandas DataFrame obtained from get_logs function.
        fight_info: pandas DataFrame obtained from extract_fights function.
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
            'difficulty',
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
    fight_df = extract_fights(boss_list, unwanted_players)

    create_master_list(log_info, fight_df)

def import_clean_master_list():
    '''
    Imports data from 'master_list.csv' as created by get_log_master_list
    function.
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

def player_info_query(player_name, guild_info, metric, api_key, partition=0):
    '''
    Queries Warcraft Logs api for player rankings from guild info according to
    the metric and manages paramaters if applicable.
    Saves json file of query data.

    args:
        player_name: (str) player name
        guild_info: dict of guild info with three keys 'guild_name', 'realm',
            'region'.
        metric: (str) one of 'hps', 'dps', 'tankhps'
        api_key: (str) of Public Warcarft Logs API key
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
        print("Missed data for", player_name, ": not in guild")

def import_player_info(player_names, guild_info, api_key, partition=1):
    '''
    Queries Warcraft Logs api for players' rankings for hps, dps and tankhps.
    Saves json file of query data.

    args:
        player_names: list of player names
        guild_info: dict of guild info with three keys 'guild_name', 'realm',
            'region'.
        api_key: (str) of Public Warcarft Logs API key
    returns:
        None
    '''
    metrics = ['hps', 'dps', 'tankhps']

    for player in player_names:
        for metric in metrics:
            player_info_query(player, guild_info, metric, api_key,
                              partition=partition)

def create_rankings_df(player_name, metric, primary_role):
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
        file_name = 'player_rankings/' + player_name + '_' + metric + \
                    '_player_rankings.txt'
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

def get_player_rankings():
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
            player_df = create_rankings_df(player,
                                           metric,
                                           player_list[player_list.player == player]['primary_role'].iloc[0])
            # Join to df
            df = pd.concat([df, player_df])

    # Clean df
    df.percentile = df.percentile.astype('int')
    df.ilevel = df.ilevel.astype('int')

    # Save df
    df.to_csv('player_rankings.csv', index=False, encoding='iso-8859-1')

    return df

def clean_player_rankings(df):
    '''
    Cleans pandas DataFrame generated from importing csv generated by
    get_player_rankings.

    args:
        pandas DataFrame.
    returns:
        pandas DataFrame.
    '''
    # Reformat to category
    df.player_name = df.player_name.astype('category')
    df.spec = df.spec.astype('category')
    df.metric = df.metric.astype('category')
    # Reformat to string
    df.boss_id = df.boss_id.astype('str')
    # Reformat to int
    df.percentile = df.percentile.astype('int')
    df.ilevel = df.ilevel.astype('int')

    return df

def import_clean_player_rankings():
    '''
    Imports data from 'player_rankings.csv' as created by get_player_rankings
    function. Reformats data for further analysis.

    args:
        None.
    returns:
        pandas DataFrame.
    '''
    # Read in player_rankings
    df = pd.read_csv('player_rankings.csv', encoding='iso-8859-1')

    # Reformat columns
    df = clean_player_rankings(df)
    df.ranking_date = pd.to_datetime(df.ranking_date, unit='ms').dt.date

    return df

def get_log_ids(df, boss_id=None):
    '''
    Collects list of unique boss ids.

    args:
        df: pandas DataFrame from get_logs.
        boss_id: (int) Code for boss encounter as defined in World of Warcraft.
    returns:
        list-like object of log ids.
    '''
    if boss_id is None:
        logs = df['log_id'].unique()
    else:
        logs = df[df.boss_id == boss_id].log_id.unique()

    return logs

def create_link(api_key,
                log_type,
                log_df,
                log,
                spell_id=None,
                boss_id=None,
                difficulty=5,
                death_cutoff=None):
    '''
    Creates link for Warcraft Logs API query.
    args:
        api_key: (str) Public Key from personal Warcraft Logs account.
        log_type: (str) One of 'damage-taken', 'casts', 'buffs' or 'debuffs'.
        log_df: pandas DataFrame from get_logs.
        log: (str) Log ID for log from Warcraft Logs.
        spell_id: (int) Code for spell as defined in World of Warcraft.
        boss_id: (int) Code for boss encounter as defined in World of Warcraft.
        death_cutoff: (int) Exclude data after this many deaths.
    returns:
        (str) Link for Warcraft Logs API query.
    '''
    # Create link components
    end = log_df[log_df['log_id'] == log].pull_end.max()
    link_start = 'https://www.warcraftlogs.com:443/v1/report/tables/'
    end_info = '?end=' + str(end) + '&'
    by_info = 'by=source&'
    ability_info = 'abilityid=' + str(spell_id) + '&'
    if spell_id is None:
        ability_info = ''
    cutoff_info = 'cutoff=' + str(death_cutoff) + '&'
    if death_cutoff is None:
        cutoff_info = ''
    boss_info = 'encounter=' + str(boss_id) + '&'
    if boss_id is None:
        boss_info = ''
    link_end = 'difficulty=' + str(difficulty) + '&api_key=' + api_key

    # Create link
    link = link_start + log_type + '/' + log + end_info + by_info + \
           ability_info + cutoff_info + boss_info + link_end
    return link

def create_link_damage_done(api_key, log_df, log, boss_id=None):
    '''
    Creates link for Warcraft Logs API query for damage done to enemies.
    args:
        api_key: (str) Public Key from personal Warcraft Logs account.
        log_df: pandas DataFrame from get_logs.
        log: (str) Log ID for log from Warcraft Logs.
        boss_id: (int) Code for boss encounter as defined in World of Warcraft.
    returns:
        (str) Link for Warcraft Logs API query.
    '''
    # Create link components
    end = log_df[log_df['log_id'] == log].pull_end.max()
    link_start = 'https://www.warcraftlogs.com:443/v1/report/tables/damage-taken/'
    end_info = '?end=' + str(end) + '&'
    target_info = 'hostility=1&by=target&'
    boss_info = 'encounter=' + str(boss_id) + '&'
    if boss_id is None:
        boss_info = ''
    link_end = 'difficulty=5&api_key=' + api_key

    # Create link
    link = link_start + log + end_info + target_info + boss_info + link_end

    return link

def get_query_details(link):
    '''
    Obtain Warcraft Logs API query details.
    args:
        link: (str) API query hyperlink.
    returns:
        json file info.
    '''
    event = requests.get(link)
    return event.json()

def drop_spell_name(df, spell_name):
    '''
    Conditional drop of 'spell_name' column from dataframe.
    args:
        df: pandas DataFrame with 'spell_name' column.
        spell_name: One of None or (str) of spell name.
    returns:
        None.
    '''
    if spell_name is None:
        df.drop('spell_name', axis=1, inplace=True)

def drop_description(df, description):
    '''
    Conditional drop of 'description' column from dataframe.
    args:
        df: pandas DataFrame with 'description' column.
        spell_name: One of None or (str) of description.
    returns:
        None.
    '''
    if description is None:
        df.drop('description', axis=1, inplace=True)

def damage_taken(api_key,
                 log_df,
                 spell_id,
                 spell_name=None,
                 boss_id=None,
                 hit_type='hitCount',
                 death_cutoff=None):
    '''
    Completes a 'damage-taken' query of the Warcraft Logs API.
    args:
        api_key: (str) Public Key from personal Warcraft Logs account.
        log_df: pandas DataFrame from get_logs.
        spell_id: (int) Code for spell as defined in World of Warcraft.
        spell_name: Optional. (str) Name of spell.
        boss_id: Optional. (int) Code for boss encounter as defined in World of
        Warcraft.
        death_cutoff: (int) Exclude data after this many deaths.
    returns:
        df: pandas DataFrame.
    '''
    df_list = []
    logs = get_log_ids(log_df, boss_id)
    for log in logs:
        print('Collecting details for log', log)

        # Complete query
        link = create_link(api_key,
                           'damage-taken',
                           log_df,
                           log,
                           spell_id,
                           boss_id,
                           death_cutoff=death_cutoff)
        details = get_query_details(link)

        # Get player info
        for player in details['entries']:
            name = player['name']
            print('Player added:', name)
            hits = player[hit_type]
            damage = player['total']
            df_list.append({
                'log_id': log,
                'spell_id': spell_id,
                'spell_name': spell_name,
                'player': name,
                'hits': hits,
                'damage_taken': damage
            })

    # Create dataframe
    df = pd.DataFrame(df_list,
                      columns=['log_id',
                               'spell_id',
                               'spell_name',
                               'player',
                               'hits',
                               'damage_taken'])
    if not spell_name:
        drop_spell_name(df, spell_name)

    return df

def buff_duration(api_key,
                  log_df,
                  spell_id,
                  spell_name=None,
                  description=None,
                  boss_id=None,
                  buff=True):
    '''
    Completes a 'buffs' or 'debuffs' query of the Warcraft Logs API.
    args:
        api_key: (str) Public Key from personal Warcraft Logs account.
        log_df: pandas DataFrame from get_logs.
        spell_id: (int) Code for spell as defined in World of Warcraft.
        spell_name: Optional. (str) Name of spell.
        boss_id: Optional. (int) Code for boss encounter as defined in World of
        Warcraft.
    returns:
        df: pandas DataFrame.
    '''
    df_list = []
    logs = get_log_ids(log_df, boss_id)
    for log in logs:
        print('Collecting details for log', log)

        # Complete query
        buff_type = 'buffs'
        if buff is False:
            buff_type = 'debuffs'
        link = create_link(api_key, buff_type, log_df, log, spell_id, boss_id)
        details = get_query_details(link)

        # Get player info
        for player in details['auras']:
            name = player['name']
            print('Player added:', name)
            duration = player['totalUptime']
            uses = player['totalUses']
            df_list.append({
                'log_id': log,
                'spell_id': spell_id,
                'spell_name': spell_name,
                'description': description,
                'player': name,
                'duration': duration,
                'uses': uses
            })

    # Create dataframe
    df = pd.DataFrame(df_list,
                      columns=['log_id',
                               'spell_id',
                               'spell_name',
                               'description',
                               'player',
                               'duration',
                               'uses'])
    drop_spell_name(df, spell_name)
    drop_description(df, description)

    return df

def cast_count(api_key,
               log_df,
               spell_id,
               spell_name=None,
               boss_id=None):
    '''
    Completes a 'casts' query of the Warcraft Logs API.
    args:
        api_key: (str) Public Key from personal Warcraft Logs account.
        log_df: pandas DataFrame from get_logs.
        spell_id: (int) Code for spell as defined in World of Warcraft.
        spell_name: Optional. (str) Name of spell.
        boss_id: Optional. (int) Code for boss encounter as defined in World of
        Warcraft.
    returns:
        df: pandas DataFrame.
    '''
    df_list = []
    logs = get_log_ids(log_df, boss_id)
    for log in logs:
        print('Collecting details for log', log)

        # Complete query
        link = create_link(api_key, 'casts', log_df, log, spell_id, boss_id)
        details = get_query_details(link)

        # Get player info
        for player in details['entries']:
            name = player['name']
            print('Player added:', name)
            count = player['total']
            df_list.append({
                'log_id': log,
                'spell_id': spell_id,
                'spell_name': spell_name,
                'player': name,
                'count': count
            })

    # Create dataframe
    df = pd.DataFrame(df_list,
                      columns=['log_id',
                               'spell_id',
                               'spell_name',
                               'player',
                               'count'])
    drop_spell_name(df, spell_name)

    return df

def damage_done(api_key, log_df, boss_id=None, NPC=True):
    '''
    Completes a 'damage-taken' by enemies query of the Warcraft Logs API.
    args:
        api_key: (str) Public Key from personal Warcraft Logs account.
        log_df: pandas DataFrame from get_logs.
        boss_id: Optional. (int) Code for boss encounter as defined in World of
        Warcraft.
        NPC: (bool) If True only damage to NPCs is calculated, if False, only
        damage to Boss.
    returns:
        df: pandas DataFrame.
    '''
    df_list = []
    logs = get_log_ids(log_df, boss_id)
    for log in logs:
        print('Collecting details for log', log)

        # Complete query
        link = create_link_damage_done(api_key, log_df, log, boss_id)
        details = get_query_details(link)

        # Get player info
        for player in details['entries']:
            if player['type'] == 'Pet':
                continue
            name = player['name']
            print('Player added:', name)
            damage = 0
            # Collect damage for NPC or boss
            for target in player['targets']:
                if NPC is True:
                    if target['type'] == 'NPC':
                        damage += target['total']
                else:
                    if target['type'] == 'Boss':
                        damage += target['total']
            df_list.append({
                'log_id': log,
                'player': name,
                'NPC': NPC,
                'damage_done': damage
            })

    # Create dataframe
    df = pd.DataFrame(df_list, columns=['log_id', 'player', 'NPC', 'damage_done'])

    return df
