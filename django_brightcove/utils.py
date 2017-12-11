import requests

from django.conf import settings
from django.utils.dateparse import parse_datetime

from .models import BrightcoveItems


RETRY_LIMIT = 2


class BrightcoveApi():
    """Class managing communication with the Brightcove API though the brightcove app."""
    account_id = ''
    client_id = ''
    client_secret = ''
    connector = None

    def __init__(self, account_id='', client_id='', client_secret=''):
        if account_id:
            self.account_id = account_id
        if not self.account_id:
            self.account_id = getattr(settings, 'BRIGHTCOVE_ACCOUNT_ID', None)
        if not self.account_id:
            raise Exception(
                "Brightcove Account ID must be provided as 'account_id' init"
                " param or Django setting 'BRIGHTCOVE_ACCOUNT_ID'")

        if client_id:
            self.client_id = client_id
        if not self.client_id:
            self.client_id = getattr(settings, 'BRIGHTCOVE_CLIENT_ID', None)
        if not self.client_id:
            raise Exception(
                "Brightcove Client ID must be provided as 'client_id' init"
                " param or Django setting 'BRIGHTCOVE_CLIENT_ID'")

        if client_secret:
            self.client_secret = client_secret
        if not self.client_secret:
            self.client_secret = getattr(
                settings, 'BRIGHTCOVE_CLIENT_SECRET', None)
        if not self.client_secret:
            raise Exception(
                "Brightcove Client ID must be provided as 'client_secret' init"
                " param or Django setting 'BRIGHTCOVE_CLIENT_SECRET'")

        self.connector = BrightcoveConnector(
            self.client_id, self.client_secret)

    def get_by_id(self, video_id):
        video = self.connector.find_video_by_id(self.account_id, video_id)
        if video:
            return self._save_item(video)
        return None

    def _get_list(self):
        return self.connector.find_all_videos(self.account_id)

    def synchronize_list(self):
        """
        Synchronizes the list of videos form a brightcove account with the
        BrightcoveItem model.
        """
        items = self._get_list()
        existing_ids = []
        for item in items.items:
            self._save_item(item)
            existing_ids.append(item['id'])
        BrightcoveItems.objects.exclude(brightcove_id__in=existing_ids).delete()

    def _save_item(self, item):
        brightcove_item, created = BrightcoveItems.objects.get_or_create(
            brightcove_id=item['id'])
        brightcove_item.name = item['name']
        brightcove_item.video_still_URL = item['images']['poster']['src']
        brightcove_item.thumbnail_URL = item['images']['thumbnail']['src']
        brightcove_item.short_description = item['description']
        brightcove_item.long_description = item.get('long_description')
        brightcove_item.length = item['duration']
        if item['link']:
            brightcove_item.link_URL = item['link']['url']
        brightcove_item.creation_date = parse_datetime(
            item['created_at'])
        brightcove_item.published_date = parse_datetime(
            item['published_at'])
        # TODO Play count is no longer available from the CMS API and I don't
        # know where it can be retrieved
        # brightcove_item.plays_total = item.get('plays_total', 0)
        brightcove_item.save()
        return brightcove_item


class BrightcoveConnector(object):

    def __init__(self, client_id, client_secret):
        self.client_id = client_id
        self.client_secret = client_secret
        self.access_token = None

    def _refresh_oauth_access_token(self):
        """
        See https://support.brightcove.com/overview-oauth-api-v4
        """
        response = requests.post(
            'https://oauth.brightcove.com/v4/access_token',
            auth=(self.client_id, self.client_secret),
            data={'grant_type': 'client_credentials'},
        )
        if response.status_code != 200:
            raise Exception(
                "Failed OAuth access token authentication for client ID '%s'"
                % self.client_id)
        token_data = response.json()
        if not token_data.get('token_type') == 'Bearer':
            raise Exception(
                "Unexpected OAuth access token response data"
                ", token_type != 'Bearer': %s"
                % token_data)
        # TODO: Store and track 'expires_in'? Currently 401 triggers re-auth
        self.access_token = token_data['access_token']

    def _request_with_retry(self, url, method='get'):
        """
        Retry a request up to `RETRY_LIMIT` times, re-authenticating when
        necessary to get a valid OAuth access token.
        """
        method_fn = getattr(requests, method)
        for i in range(RETRY_LIMIT):
            if not self.access_token:
                self._refresh_oauth_access_token()
            response = method_fn(
                url,
                headers={
                    'Authorization': 'Bearer %s' % self.access_token,
                    'Content-Type': 'application/json',
                }
            )
            # If auth failed, reset access token in preparation to try again
            if response.status_code == 401:
                self.access_token = None
            # Return data from successful response immediately, after checking
            # for error conditions for all response codes where we expect to
            # get JSON data
            if response.status_code in [200, 400, 401, 404]:
                response_data = response.json()
                # Parse error response data and package in exception
                if response.status_code != 200:
                    raise Exception(
                        "Brightcove API request failed with error: %s - %s"
                        % (response_data[0]['error_code'],
                           response_data[0]['message']))
                return response_data
        # Return last unsuccessful response
        raise Exception("Brightcove API request failed: %s" % response)

    def find_video_by_id(self, account_id, video_id):
        """
        Fetch video metadata by video's ID and return a dict of the JSON
        response.

        See https://brightcovelearning.github.io/Brightcove-API-References/cms-api/v1/doc/index.html#api-videoGroup-Get_Video_by_ID_or_Reference_ID
        """
        url = 'https://cms.api.brightcove.com/v1/accounts/%s/videos/%s' \
            % (account_id, video_id)
        return self._request_with_retry(url)

    def find_video_by_reference_id(self, account_id, reference_id):
        """
        Fetch video metadata by video's reference ID and return a dict of the
        JSON response.

        See https://brightcovelearning.github.io/Brightcove-API-References/cms-api/v1/doc/index.html#api-videoGroup-Get_Video_by_ID_or_Reference_ID
        """
        url = 'https://cms.api.brightcove.com/v1/accounts/%s/videos/ref:%s' \
            % (account_id, reference_id)
        return self._request_with_retry(url)

    def find_all_videos(self, account_id):
        """
        Fetch metadata for a set of by video's and return a dict of the
        JSON response.

        See https://brightcovelearning.github.io/Brightcove-API-References/cms-api/v1/doc/index.html#api-videoGroup-Get_Videos
        """
        url = 'https://cms.api.brightcove.com/v1/accounts/%s/videos' \
            % account_id
        return self._request_with_retry(url)
