import os
import json
from typing import Optional

from python_git_wrapper import Repository, GitError

import hashlib

MERGE_STRING = "Merge pull request"
README_STRING = "Update README.md"


class Cache(object):

    __slots__ = ["_cache_location", "_json"]

    def __init__(self,
                 cache_location: str,
                 override_location: Optional[str] = None):
        self._cache_location = cache_location
        self._json = Cache._get_cache(cache_location, override_location)

    def update(self, repository: Repository):
        for commit in self.walk_commit(repository):
            author = commit.author
            if author in self.alias:
                author = self.alias[author]
            if author not in self.commits:
                self.commits[author] = []
            self.visited.append(commit.hash)
            self.commits[author].append(str(commit.datetime.date()))
            if author not in self.authors:
                self.authors[author] = commit.email
            print(author, commit.hash, commit.message, commit.datetime)

    def dump(self):
        with open(self._cache_location, "w") as cache:
            return json.dump(self._json, cache, sort_keys=True, indent=4)

    def walk_commit(self, repository: Repository):
        visited = set(
            repository.get_commit(visited) for visited in self.visited)
        search = set([repository.last_commit]) - visited
        while search:
            commit = search.pop()
            search |= set(commit.parents) - visited
            visited.add(commit)
            if (MERGE_STRING not in commit.message
                    and README_STRING not in commit.message):
                yield commit

    def __getattr__(self, key: str):
        if key.startswith("_"):
            super().__getattr__(key)
        if key not in self._json:
            raise AttributeError(f"Cache key not found: {key}.")
        return self._json[key]

    @staticmethod
    def _get_cache(cache_location: str,
                   override_location: Optional[str] = None):

        template = {
            "visited": [],
            "commits": {},
            "authors": {},
            "alias": {},
            "override": ""
        }
        data = template.copy()
        if os.path.exists(cache_location):
            with open(cache_location) as cache:
                data.update(json.load(cache))
        if override_location:
            with open(override_location) as override:
                override_string = override.read()
                hash = hashlib.md5(override_string.encode('utf-8')).hexdigest()
            override = json.loads(override_string)
            if data["override"] is not hash:
                data = template.copy()
                data["override"] = hash
            data.update(override)

        return data
