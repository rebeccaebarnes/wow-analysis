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
