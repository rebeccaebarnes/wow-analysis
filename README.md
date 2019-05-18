# Tempest Raid Analysis
## Overview
[Tempest](https://tempest-proudmoore.enjin.com/) is a World of Warcraft raiding guild on Proudmoore. I do analysis of our guild logs via the [Warcraft Logs](https://www.warcraftlogs.com/) API.

There are two primary types of analysis that are completed - analysis to understand and improve our performance while raiding and analysis to create our guild awards at the end of a tier. The full data analysis process is completed including gathering, wrangling, and EDA. Areas of exploration include number of casts of certain spells, damage taken from specific abilities, healing done to specific players, damage done to particular enemies. Alternate names used or characters played are managed and player roles are considered.

The most recent guild awards analysis can be found [here](https://github.com/rebeccaebarnes/wow-analysis/blob/master/uldir_guild_awards.ipynb).

**If you've found this helpful, please consider forking, rather than cloning this repo.**

## Technologies Used
- Python
- Libraries: numpy, pandas, matplotlib, seaborn, json, requests, os
- Personal modules: [log_analysis](https://github.com/rebeccaebarnes/wow-analysis/blob/master/log_analysis.py), [warcraft_logs_fn](https://github.com/rebeccaebarnes/wow-analysis/blob/master/warcraft_logs_fn.py) (Note: The Warcraft Logs API is not a closed API due to ongoing development by Blizzard. As a result, these functions may require updating from time to time)
- Jupyter Notebooks
