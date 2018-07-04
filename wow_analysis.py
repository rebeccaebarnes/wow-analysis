GUILD_NAME = 'Last%20Pull'
REALM = 'Cenarius'
REGION = 'US'

def get_log_master_list(api_key,
                        boss_list,
                        log_start=None,
                        unwanted_players=None):
    '''
    Extracts mythic log information for World of Warcraft guild, Last Pull,
        on Cenarius, and saves in 'master_list.csv'.
    Requires import of the following libraries: pandas as pd, numpy as np,
        requests, json, os

    args:
        api_key: (str) Public Key from personal Warcraft Logs account
        boss_list: list of strings of boss names, as recorded by Warcraft Logs
        log_start: optional. (int) unix time stamp for log start date
        unwanted_players: optional. list of player names to exclude
    returns:
        pandas DataFrame
    '''
    # Gather all guild logs
    link = "https://www.warcraftlogs.com:443/v1/reports/guild/" + GUILD_NAME +\
            "/" + REALM + "/" + REGION + "/US?api_key="
    guild_logs = requests.get(link + api_key)
    log_list = guild_logs.json()
    # Convert to df
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

    print("Logs gathered.\n")

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
    for log_id in log_info.log_id:
        # Open file
        filename = 'log_details/' + log_id + '_log_details.txt'
        with open(filename) as json_file:
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

    # Merge log_info and df
    df = df.merge(log_info, how="left", on="log_id")
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

    return df

def import_clean_master_list():
    '''
    Imports data from 'master_list.csv' as created by get_log_master_list function.
    Reformats data for further analysis.
    Requires import of the following libraries: pandas

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
