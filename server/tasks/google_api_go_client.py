# Copyright 2017, Google Inc. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Contains update/release functions for google-api-go-client."""

import re
from datetime import date

import os
from os.path import join

from tasks import _commit_message, _git
from tasks._check_output import check_output

# Matches strings like "foo/v1/foo-gen.go".
_NAME_VERSION_RE = re.compile(r'(.+)/(.+)/.+\.go')
_REMOTE_URL = 'https://code.googlesource.com/_direct/google-api-go-client'


def _generate_all_clients(repo, env):
    generator_filepath = join(repo.filepath, 'google-api-go-generator')
    check_output(['make', 'all'], cwd=generator_filepath, env=env)
    added, deleted, updated = set(), set(), set()
    for filename, status in repo.diff_name_status(staged=False):
        match = _NAME_VERSION_RE.match(filename)
        if not match:
            continue
        name_version = '{}/{}'.format(match.group(1), match.group(2))
        {
            _git.Status.ADDED: added,
            _git.Status.DELETED: deleted,
            _git.Status.UPDATED: updated
        }.get(status, set()).add(name_version)
    return added, deleted, updated


def update(filepath, github_account):
    """Updates the google-api-go-client repository.

    Args:
        filepath (str): the directory to work in.
        github_account (GitHubAccount): the GitHub account to commit with.
    """
    env = os.environ.copy()
    env['GOPATH'] = filepath
    check_output(['go', 'get', '-d', '-t', 'google.golang.org/api/...'],
                 env=env)
    repo = _git.Repository(join(filepath, 'src/google.golang.org/api'))
    added, deleted, updated = _generate_all_clients(repo, env)
    if not any([added, deleted, updated]):
        return
    check_output(['go', 'test', './...'], cwd=repo.filepath, env=env)
    subject = 'all: autogenerated update ({})'.format(date.today().isoformat())
    commitmsg = _commit_message.build(added, deleted, updated, subject=subject)
    repo.add(['.'])
    repo.commit(commitmsg, github_account.name, github_account.email)
    repo.push(remote=_REMOTE_URL)
