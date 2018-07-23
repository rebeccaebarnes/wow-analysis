import pandas as pd
import warcraft_logs_fn as wl

def max_parses(df, player_name, primary_role):
    '''
    Creates df of player maximum parse per boss passed on appropriate metric
    for primary_role.

    args:
        df: pandas DataFrame from wl.import_clean_player_rankings.
        player_name: (str) player's name.
        primary_role: (str) primary role assigned to fight.
    returns:
        pandas DataFrame.
    '''
    # Confirm metric
    if primary_role == 'damage':
        metric = 'dps'
    if primary_role == 'healer':
        metric = 'hps'
    if primary_role == 'tank':
        metric = 'tankhps'

    # Create df of only player and primary role/metric info
    player_df = df[(df.player_name == player_name) & (df.metric == metric)]
    index_list = []

    # Find rows with max parses
    for boss in player_df.boss_name:
        boss_rows = player_df[(player_df.boss_name == boss)]
        # Manage bosses with rankings for multiple specs
        if boss_rows.shape[0] > 1:
            index = boss_rows.percentile.idxmax()
        else:
            index = boss_rows.index[0]
        index_list.append(index)
    index_list = list(set(index_list))
    index_list

    # Create parse df from index_list
    return player_df.loc[index_list]

def extract_max_parses():
    '''
    Creates df of max parses for all players from import_clean_player_rankings.
    Removes parses played in a spec not aligned with primary_role.
    Imports from pre-existing files: 'player_list.csv', 'class_info.csv'

    args:
        None.
    returns:
        pandas DataFrame.
    '''
    # Read in parse info
    df = wl.import_clean_player_rankings()

    # Create empty df with same columns
    cols = df.columns
    parses_df = pd.DataFrame([], columns=cols)

    # Find player names
    player_names = list(df.player_name.unique())

    # Get player primary role
    player_info = pd.read_csv('player_list.csv', encoding='iso-8859-1')

    # Read in class info
    class_info = pd.read_csv('class_info.csv')

    # Get player max parses
    for player in player_names:
        # Extract primary role from first row
        primary_role = player_info[player_info.player == player]['primary_role'].iloc[0]
        player_df = max_parses(df, player, primary_role)
        # Remove rows with wrong spec
        for index, row in player_df.iterrows():
            spec = row.spec
            # Check if spec is in class role list
            spec_test = ((class_info.role == primary_role) & (class_info.spec == spec)).sum()
            # If not, drop from df
            if spec_test == 0:
                player_df.drop(index, inplace=True)
        # Add onto parses_df
        parses_df = pd.concat([parses_df, player_df])

    # Clean parses_df
    parses_df = wl.clean_player_rankings(parses_df)

    return parses_df

def change_names(df, player_names):
    '''
    Change alt player names retrieved from Warcraft Logs API query to player
    names.
    args:
        df: pandas DataFrame with 'player' column.
        player_names: pandas DataFrame from player_list.csv.
    returns:
        None.
    '''
    players = player_names['alt'].unique()
    for index, row in df.iterrows():
        player_name = row['player']
        if player_name in players:
            df.at[index, 'player'] = player_names[player_names['alt'] == player_name].player.iloc[0]


def presence_count(log_df, boss_id):
    '''
    Counts all player appearances for a particular boss from logs.

    args:
        log_df: pandas DataFrame from master_list.csv.
        boss_id: (int) Code for boss encounter as defined in World of Warcraft.
    returns:
        pandas DataFrame.
    '''
    # Limit log_df to only those with boss_id
    boss_fights = log_df[log_df['boss_id'] == boss_id]

    # Create df of player count within log
    df_list = []
    for player in log_df['player_name'].unique():
        count = boss_fights[boss_fights['player_name'] == player].shape[0]
        df_list.append({
            'boss_id': boss_id,
            'player': player,
            'fight_count': count
        })

    df = pd.DataFrame(df_list, columns=['boss_id', 'player', 'fight_count'])
    return df

def join_fight_count(fight_df, log_df, boss_id):
    '''
    Joins fight count to fight df.
    args:
        fight_df: pandas DataFrame of fight statistics.
        log_df: pandas DataFrame from master_list.csv.
        boss_id: (int) Code for boss encounter as defined in World of Warcraft.
    returns:
        pandas DataFrame.
    '''
    # Get player fight count
    fight_count = presence_count(log_df, boss_id)

    # Join fight count to fight_df
    df = fight_df.merge(fight_count[['player', 'fight_count']], how='left', on='player')

    return df

def join_player_roles(fight_df, player_names):
    '''
    Adds player roles to fight statistics.

    args:
        fight_df: pandas DataFrame of fight statistics.
        player_names: pandas DataFrame from player_list.csv.
    returns:
        pandas DataFrame.
    '''
    df = fight_df.merge(player_names[['player', 'primary_role']], how='left', on='player')
    return df

def clean_damage_fight_count(fight_df, log_df, player_names, boss_id):
    '''
    Adds fight counts, substitute alt names and combines with substituted names.

    args:
        fight_df: pandas DataFrame of fight statistics.
        log_df: pandas DataFrame from master_list.csv.
        player_names: pandas DataFrame from player_list.csv.
        boss_id: (int) Code for boss encounter as defined in World of Warcraft.
    returns:
        pandas DataFrame.
    '''
    # Sum stats by player
    df = fight_df.groupby('player')[['player', 'hits', 'damage_taken']].sum().reset_index()
    # Join hit counts
    df = join_fight_count(df, log_df, boss_id)
    # Manage alts
    change_names(df, player_names)
    df = df.groupby('player').sum().reset_index()
    # Join player role
    df = join_player_roles(df, player_names)

    return df

def find_count_order(fight_df, fight_count_limit, column_name, least=True):
    '''
    Finds order of average action within at least minimum fight count.

    args:
        fight_df: pandas DataFrame of fight statistics with fight count numbers.
        fight_count_limit: Minimum number of fights a player must have to be
        included.
        column_name: (str) Column of action to be averaged.
        least: (bool) If least is True will sort in ascending order, if False,
        in descending order.
    returns:
        pandas DataFrame.
    '''
    # Copy to avoid warning messages
    df = fight_df.copy()

    # Create average hits per fight column
    df['av_count'] = df[column_name] / df['fight_count']

    # Limit df to above fight_count_limit
    df = df[df['fight_count'] >= fight_count_limit]

    # Sort av_hits
    df.sort_values('av_count', ascending=least, inplace=True)

    return df
