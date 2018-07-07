def max_parses(df, player_name, primary_role):
    # Create df of only player and primary role info
    player_df = df[(df.player_name == player_name) & (df.primary_role == primary_role)]
    index_list = []
    # Find rows with max parses
    for boss in player_df.boss_name:
        boss_rows = player_df[player_df.boss_name == boss]
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
