###
# Copyright (c) 2014, spline
# All rights reserved.
#
#
###
# my libs
import json
import cgi
# supybot libs
import supybot.utils as utils
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks
# extra supybot libs
import supybot.ircmsgs as ircmsgs
import supybot.world as world
import supybot.log as log
import supybot.httpserver as httpserver
try:
    from supybot.i18n import PluginInternationalization
    _ = PluginInternationalization('WebHooks')
except ImportError:
    # Placeholder that allows to run the plugin on a bot
    # without the i18n module
    _ = lambda x:x

def flatten_subdicts(dicts, flat=None):
    """Change dict of dicts into a dict of strings/integers. Useful for
    using in string formatting."""
    if flat is None:
        # Instanciate the dictionnary when the function is run and now when it
        # is declared; otherwise the same dictionnary instance will be kept and
        # it will have side effects (memory exhaustion, ...)
        flat = {}
    if isinstance(dicts, list):
        return flatten_subdicts(dict(enumerate(dicts)))
    elif isinstance(dicts, dict):
        for key, value in dicts.items():
            if isinstance(value, dict):
                value = dict(flatten_subdicts(value))
                for subkey, subvalue in value.items():
                    flat['%s__%s' % (key, subkey)] = subvalue
            else:
                flat[key] = value
        return flat
    else:
        return dicts

# [GitPull] reticulatingspline pushed 1 commit to master [+0/-0/1] http://git.io/n4lbSQ
# [GitPull] spline e2070d1 - Fix initial test as I forgot it might actually update.
# [Assorted] Travis CI - build #73 passed. (master @ 3c4572b) http://git.io/OhYANw
# [Assorted] Details: https://travis-ci.org/reticulatingspline/Assorted/builds/38050581
# [Assorted] reticulatingspline pushed 1 commit to master [+0/-0/+1] http://git.io/OhYANw
# [Assorted] spline 3c4572b - Turn off logURLs by default.


def format_push(d):
    """Format a push for IRC."""
    
    try:
        reponame = d['repository__name']
        commit_msg = d['head_commit__message']
        committer = d['commits'][0]['committer']['name']
        numofc = len(d['commits'])
        branch = d['repository__master_branch']
        compare = d['compare']
        m = "[{0}] {1} pushed {2} commit to {3} {4} {5}".format(reponame, committer, numofc, branch, commit_msg, compare)
        return m
        #u'repository__homepage': u'',
        #u'head_commit__distinct': True,
        #u'before': u'd0b89abde1fba07213f214bc270ad3e333f7c9f8',
        #u'repository__fork': False,
        #u'head_commit__modified': [u'plugin.py'],
        #u'repository__open_issues_count': 0,
        #u'head_commit__id': u'dee5761e60ce0da4babe836a4eb774160f7ee5d7',
        #u'repository__watchers': 1,
        #u'repository__updated_at': u'2014-10-16T13:12:53Z',
        #u'repository__private': False,
        #u'repository__size': 286,
        #u'repository__comments_url': u'https://api.github.com/repos/reticulatingspline/WolframAlpha/comments{/number}',
        #u'repository__html_url': u'https://github.com/reticulatingspline/WolframAlpha',
        #u'sender__avatar_url': u'https://avatars.githubusercontent.com/u/1811535?v=2',
        #u'repository__has_issues': True,
        #u'repository__archive_url': u'https://api.github.com/repos/reticulatingspline/WolframAlpha/{archive_format}{/ref}',
        #u'sender__login': u'reticulatingspline',
        #u'base_ref': None,
        #u'repository__issue_events_url':
        #u'https://api.github.com/repos/reticulatingspline/WolframAlpha/issues/events{/number}',
        #u'repository__forks_count': 1,
        #u'repository__issue_comment_url': u'https://api.github.com/repos/reticulatingspline/WolframAlpha/issues/comments/{number}',
        #u'repository__pushed_at': 1413471664,
        #u'repository__default_branch': u'master',
        #u'head_commit__author__name': u'spline',
        #u'sender__url': u'https://api.github.com/users/reticulatingspline',
        #u'sender__received_events_url': u'https://api.github.com/users/reticulatingspline/received_events',
        #u'repository__git_refs_url': u'https://api.github.com/repos/reticulatingspline/WolframAlpha/git/refs{/sha}',
        #u'repository__downloads_url': u'https://api.github.com/repos/reticulatingspline/WolframAlpha/downloads',
        #u'sender__following_url': u'https://api.github.com/users/reticulatingspline/following{/other_user}',
        #u'repository__svn_url': u'https://github.com/reticulatingspline/WolframAlpha',
        #u'head_commit__message': u'Modernize plugin.',
        #u'repository__has_downloads': True,
        #u'sender__site_admin': False,
        #u'ref': u'refs/heads/master',
        #u'repository__owner__name': u'reticulatingspline',
        #u'after': u'dee5761e60ce0da4babe836a4eb774160f7ee5d7',
        #u'deleted': False,
        #u'commits':
        #    [{u'committer':
        #        {u'name': u'spline',
        #         u'email': u'reticulatingspline@github.com'},
        #         u'added': [],
        #         u'author': {u'name': u'spline', u'email': u'reticulatingspline@github.com'},
        #         u'distinct': True,
        #         u'timestamp': u'2014-10-16T11:01:02-04:00',
        #         u'modified': [u'plugin.py'],
        #         u'url': u'https://github.com/reticulatingspline/WolframAlpha/commit/dee5761e60ce0da4babe836a4eb774160f7ee5d7',
        #         u'message': u'Modernize plugin.',
        #         u'removed': [],
        #         u'id': u'dee5761e60ce0da4babe836a4eb774160f7ee5d7'}],
        #u'repository__master_branch': u'master',
        #u'repository__git_commits_url': u'https://api.github.com/repos/reticulatingspline/WolframAlpha/git/commits{/sha}',
        #u'repository__trees_url': u'https://api.github.com/repos/reticulatingspline/WolframAlpha/git/trees{/sha}',
        #u'repository__issues_url': u'https://api.github.com/repos/reticulatingspline/WolframAlpha/issues{/number}',
        #u'repository__mirror_url': None,
        #u'repository__labels_url': u'https://api.github.com/repos/reticulatingspline/WolframAlpha/labels{/name}',
        #u'repository__full_name': u'reticulatingspline/WolframAlpha',
        #u'created': False,
        #u'pusher__email': u'reticulatingspline@users.noreply.github.com',
        #u'sender__followers_url': u'https://api.github.com/users/reticulatingspline/followers',
        #u'head_commit__url': u'https://github.com/reticulatingspline/WolframAlpha/commit/dee5761e60ce0da4babe836a4eb774160f7ee5d7',
        #u'repository__languages_url': u'https://api.github.com/repos/reticulatingspline/WolframAlpha/languages',
        #u'repository__description': u'Limnoria / Supybot plugin to interface with Wolfram Alpha and display results on IRC. ',
        #u'repository__commits_url': u'https://api.github.com/repos/reticulatingspline/WolframAlpha/commits{/sha}',
        #u'repository__pulls_url': u'https://api.github.com/repos/reticulatingspline/WolframAlpha/pulls{/number}',
        #u'sender__type': u'User',
        #u'repository__watchers_count': 1,
        #u'sender__events_url': u'https://api.github.com/users/reticulatingspline/events{/privacy}',
        #u'repository__keys_url': u'https://api.github.com/repos/reticulatingspline/WolframAlpha/keys{/key_id}',
        #u'repository__milestones_url': u'https://api.github.com/repos/reticulatingspline/WolframAlpha/milestones{/number}',
        #u'repository__assignees_url': u'https://api.github.com/repos/reticulatingspline/WolframAlpha/assignees{/user}',
        #u'head_commit__timestamp': u'2014-10-16T11:01:02-04:00',
        #u'repository__tags_url': u'https://api.github.com/repos/reticulatingspline/WolframAlpha/tags',
        #u'repository__clone_url': u'https://github.com/reticulatingspline/WolframAlpha.git',
        #u'repository__subscribers_url': u'https://api.github.com/repos/reticulatingspline/WolframAlpha/subscribers',
        #u'repository__branches_url': u'https://api.github.com/repos/reticulatingspline/WolframAlpha/branches{/branch}',
        #u'repository__merges_url': u'https://api.github.com/repos/reticulatingspline/WolframAlpha/merges',
        #u'repository__name': u'WolframAlpha',
        #u'repository__stargazers': 1,
        #u'repository__open_issues': 0,
        #u'repository__created_at': 1354212565,
        #u'sender__organizations_url': u'https://api.github.com/users/reticulatingspline/orgs',
        #u'head_commit__author__email': u'reticulatingspline@github.com',
        #u'sender__gravatar_id': u'',
        #u'repository__git_url': u'git://github.com/reticulatingspline/WolframAlpha.git',
        #u'sender__html_url': u'https://github.com/reticulatingspline',
        #u'repository__compare_url': u'https://api.github.com/repos/reticulatingspline/WolframAlpha/compare/{base}...{head}',
        #u'head_commit__added': [],
        #u'sender__id': 1811535,
        #u'repository__forks_url':
        #u'https://api.github.com/repos/reticulatingspline/WolframAlpha/forks',
        #u'repository__forks': 1, u'repository__teams_url': u'https://api.github.com/repos/reticulatingspline/WolframAlpha/teams',
        #u'repository__ssh_url': u'git@github.com:reticulatingspline/WolframAlpha.git',
        #u'compare': u'https://github.com/reticulatingspline/WolframAlpha/compare/d0b89abde1fb...dee5761e60ce',
        #u'repository__id': 6926027,
        #u'repository__hooks_url':
        #u'https://api.github.com/repos/reticulatingspline/WolframAlpha/hooks',
        #u'repository__has_pages': True,
        #u'sender__subscriptions_url':
        #u'https://api.github.com/users/reticulatingspline/subscriptions',
        #u'repository__owner__email': u'reticulatingspline@users.noreply.github.com',
        #u'sender__gists_url': u'https://api.github.com/users/reticulatingspline/gists{/gist_id}',
        #u'repository__collaborators_url': u'https://api.github.com/repos/reticulatingspline/WolframAlpha/collaborators{/collaborator}',
        #u'forced': False,
        #u'sender__starred_url': u'https://api.github.com/users/reticulatingspline/starred{/owner}{/repo}',
        #u'repository__notifications_url': u'https://api.github.com/repos/reticulatingspline/WolframAlpha/notifications{?since,all,participating}',
        #u'repository__contributors_url': u'https://api.github.com/repos/reticulatingspline/WolframAlpha/contributors',
        #u'repository__statuses_url': u'https://api.github.com/repos/reticulatingspline/WolframAlpha/statuses/{sha}',
        #u'repository__language': u'Python',
        #u'repository__blobs_url': u'https://api.github.com/repos/reticulatingspline/WolframAlpha/git/blobs{/sha}',
        #u'sender__repos_url': u'https://api.github.com/users/reticulatingspline/repos',
        #u'repository__stargazers_count': 1,
        #u'repository__url': u'https://github.com/reticulatingspline/WolframAlpha',
        #u'head_commit__removed': [],
        #u'repository__has_wiki': False,
        #u'pusher__name': u'reticulatingspline',
        #u'head_commit__committer__name': u'spline',
        #u'repository__contents_url': u'https://api.github.com/repos/reticulatingspline/WolframAlpha/contents/{+path}',
        #u'repository__events_url': u'https://api.github.com/repos/reticulatingspline/WolframAlpha/events',
        #u'head_commit__committer__email': u'reticulatingspline@github.com'
        #}
        
    except Exception as e:
        log.info("_format_push :: ERROR :: {0}".format(e))
        return None

def format_status(d):
    """Format."""
    try:
        reponame = d['repository__name']
        commit_msg = d['head_commit__message']
        committer = d['commits'][0]['committer']['name']
        m = "{0} - {1} - {2}".format(reponame, commit_msg, committer)
        return m
    except Exception as e:
        log.info("format_status :: ERROR :: {0}".format(e))
        return None

class WebHooksServiceCallback(httpserver.SupyHTTPServerCallback):
    name = "WebHooksService"
    defaultResponse = """This plugin handles only POST request, please don't use other requests."""

    def doPost(self, handler, path, form):
        if not handler.address_string().endswith('.rs.github.com') and \
                not handler.address_string().endswith('.cloud-ips.com') and \
                not handler.address_string() == 'localhost' and \
                not handler.address_string().startswith('127.0.0.') and \
                not handler.address_string().startswith('192.30.252.') and \
                not handler.address_string().startswith('204.232.175.'):
            log.warning("""'%s' tried to act as a web hook for Github,
            but is not GitHub.""" % handler.address_string())
            self.send_response(403)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b('Error: you are not a GitHub server.'))
        else:
            # send OK back.
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write("OK")
            headers = dict(self.headers)
            # sanity/security check.
            if 'user-agent' not in headers and 'x-github-event' not in headers:
                log.info("ERROR: user-agent or x-github-event not in headers :: {0}".format(headers))
                return
            # only handle two types of events.
            if headers['x-github-event'] not in ('push', 'status'):
                log.info("ERROR: x-github-event not push or status :: {0}".format(headers))
                return
            json_payload = form.getvalue('payload')
            payload = json.loads(json_payload)
            d = flatten_subdicts(payload)
            log.info("doPost: {0}".format(d))
            # lets figure out how to handle each type of notification here.
            if headers['x-github-event'] == 'push':  # push event.
                s = format_push(d)
                if s:  # send if we get it back.
                    self.plugin._announce_webhook(s)
            elif headers['x-github-event'] == 'status':
                s = format_status(d)
                if s:  # send if we get it back.
                    self.plugin._announce_webhook(s)

class WebHooks(callbacks.Plugin):
    """Add the help for "@plugin help WebHooks" here
    This should describe *how* to use this plugin."""
    threaded = True

    def __init__(self, irc):
        self.__parent = super(WebHooks, self)
        self.__parent.__init__(irc)
        callback = WebHooksServiceCallback()
        callback.plugin = self
        httpserver.hook('webhooks', callback)

    def die(self):
        self.__parent.die()
        httpserver.unhook('webhooks')

    def _announce_webhook(self, m):
        for (server, channel) in (('efnet', '#supybot'),):
            m = "{0}".format(m)
            world.getIrc(server).sendMsg(ircmsgs.privmsg(channel, m))

Class = WebHooks


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
