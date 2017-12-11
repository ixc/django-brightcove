import requests

from django.conf import settings

from .models import BrightcoveItems


RETRY_LIMIT = 1


class BrightcoveApi():
    """Class managing communication with the Brightcove API though the brightcove app."""
    client_id = ''
    client_secret = ''
    connector = None

    def __init__(self, client_id='', client_secret=''):
        if client_id:
            self.client_id = client_id
        if not self.client_id:
            self.client_id = getattr(settings, 'BRIGHTCOVE_CLIENT_ID', None)
        if client_secret:
            self.client_secret = client_secret
        if not self.client_secret:
            self.client_secret = getattr(
                settings, 'BRIGHTCOVE_CLIENT_SECRET', None)

        self.connector = BrightcoveConnector(
            self.client_id, self.client_secret)

    def get_by_id(self, brightcove_id):
        video = self.connector.find_video_by_id(brightcove_id)
        if video:
            return self._save_item(video)
        return None

    def _get_list(self):
        return self.connector.find_all_videos()

    def synchronize_list(self):
        """Synchronizes the list of videos form a brightcove account with the BrightcoveItem model."""
        items = self._get_list()
        existing_ids = []
        for item in items.items:
            self._save_item(item)
            existing_ids.append(item['id'])
        BrightcoveItems.objects.exclude(brightcove_id__in=existing_ids).delete()

    def _save_item(self, item):
        brightcove_item, created = BrightcoveItems.objects.get_or_create(brightcove_id=item['id'])
        brightcove_item.name = item['name']
        brightcove_item.video_still_URL = item.get('videoStillURL')  # TODO Map
        brightcove_item.thumbnail_URL = item['images']['thumbnail']['src']
        brightcove_item.short_description = item['description']
        brightcove_item.long_description = item.get('long_description')
        brightcove_item.length = item['duration']
        brightcove_item.link_URL = item['link']
        brightcove_item.plays_total = item.get('playsTotal', 0)  # TODO Map
        brightcove_item.creation_date = item['created_at']  # TODO Parse
        brightcove_item.published_date = item['published_at']  # TODO Parse
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
        if response.status_code == 401:
            raise Exception(
                "Failed OAuth access token authentication for client ID '%s'"
                % self.client_id)
        token_data = response.json()
        if not token_data.get('token_type') == 'Bearer':
            raise Exception(
                "Unexpected OAuth access token response data"
                ", token_type != 'Bearer': %s"
                % token_data)
        # TODO: Store and track 'expires_in'?
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
            if response.status_code == 401:
                self.access_token = None
            if response.status_code == 200:
                return response
        return response

    def find_video_by_id(self, account_id, video_id):
        """
        See https://brightcovelearning.github.io/Brightcove-API-References/cms-api/v1/doc/index.html#api-videoGroup-Get_Video_by_ID_or_Reference_ID
        """
        url = 'https://cms.api.brightcove.com/v1/accounts/%s/videos/%s' \
            % (account_id, video_id)
        return self._request_with_retry(url).json()

    def find_video_by_reference_id(self, account_id, reference_id):
        """
        See https://brightcovelearning.github.io/Brightcove-API-References/cms-api/v1/doc/index.html#api-videoGroup-Get_Video_by_ID_or_Reference_ID
        """
        url = 'https://cms.api.brightcove.com/v1/accounts/%s/videos/ref:%s' \
            % (account_id, reference_id)
        return self._request_with_retry(url).json()

    def find_all_videos(self, account_id):
        """
        See https://brightcovelearning.github.io/Brightcove-API-References/cms-api/v1/doc/index.html#api-videoGroup-Get_Videos
        """
        url = 'https://cms.api.brightcove.com/v1/accounts/%s/videos' \
            % account_id
        return self._request_with_retry(url).json()
