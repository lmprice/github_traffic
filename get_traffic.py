from github import Github
from threading import Thread

import argparse
import os
import pandas as pd
import numpy as np
import configparser

config = configparser.ConfigParser()

class UserStats():

    def __init__(self, configFile=None):
        config.read(configFile)
        self.token = config["github"]["token"]
    
    def updateUserStats(self):
        g = Github(self.token)
        user = g.get_user()
        self.user_name = user.name
        print(f">>> Getting repo details of user {user.name} with GitHub url : {user.html_url} ...")
        repos = user.get_repos()

        threads = []

        # We're only able to retrieve repo statistics for those we can push to
        repos = [repo for repo in repos if repo.permissions.push]
        results = [None] * len(repos)

        for idx, repo in enumerate(repos):
            # Spawn a thread for each repo
            t = Thread(target=self.updateRepoStats, args=(repo, results, idx,))
            t.start()
            threads.append(t)

        # Wait for all threads to execute
        while len(threads):
            threads = [t for t in threads if t.is_alive()]

        if os.path.exists(f'{self.user_name}.csv'):
            df = pd.read_csv(f'{self.user_name}.csv')
        else:
            df = pd.DataFrame(columns=['Repo', 'Views', 'Stars', 'Watching', 'Forks', 'Clones'])
        changed = False
        # Evaluate all repo results and update output CSV accordingly
        for row in results:
            existing_entry = (df.Repo == row[0]).any()

            if existing_entry:
                if not np.array_equal(np.array(row, dtype=object), df.loc[df.Repo == row[0]].values[0]):
                    df.loc[df.Repo == row[0]] = row
                    changed=True
            else:
                df = df.append(pd.DataFrame(
                    [row], 
                    columns=['Repo', 'Views', 'Stars', 'Watching', 'Forks', 'Clones']), 
                    ignore_index=True
                )
                changed=True

        # Update output CSV only if it's outdated
        if changed:
            df.to_csv(f'{self.user_name}.csv', index=None)

    def updateRepoStats(self, repo, results, idx):
        row = [
            repo.name, 
            repo.get_views_traffic()['count'], 
            repo.stargazers_count, 
            repo.watchers_count, 
            repo.forks_count,
            repo.get_clones_traffic()['count']
        ]
        results[idx] = row

def main():
    parser = argparse.ArgumentParser(description="Download traffic stats of a GitHub user account")
    parser.add_argument("-c", metavar="config", help="config file location", required=True)
    args = parser.parse_args()

    stats = UserStats(configFile=args.c)
    stats.updateUserStats()
    print(f">>> Successfully obtained details and saved at '{stats.user_name}.csv'")

if __name__=='__main__':
    main()