from django import template
from django.conf import settings


register = template.Library()


@register.inclusion_tag('tags/brightcove_player.html',
                        takes_context=True)
def brightcove_player(context, video_id, *args, **kwargs):
    """
    This tag generates the VIDEO HTML tag to render the Brightcove Player.
    It requires the BRIGHTCOVE_PLAYER setting dict to be properly setup in
    the django setting.
    """
    if not settings.BRIGHTCOVE_PLAYER:
        raise Exception(
            "BRIGHTCOVE_PLAYER setting is missing from your settings.")
    player = kwargs.get('player', 'default')

    try:
        player = settings.BRIGHTCOVE_PLAYER[player]
    except:
        raise KeyError(
            "'%s' player type is missing from the BRIGHTCOVE_PLAYER setting"
            % player)

    # Get Brightcove Account ID from global BRIGHTCOVE_ACCOUNT_ID setting or
    # player-specific ACCOUNT_ID setting.
    try:
        context['account_id'] = settings.BRIGHTCOVE_ACCOUNT_ID
    except AttributeError:
        pass
    try:
        context['account_id'] = player['ACCOUNT_ID']
    except KeyError:
        pass
    if 'account_id' not in context:
        raise Exception(
            "Brightcove Account ID must be set as global BRIGHTCOVE_ACCOUNT_ID"
            " setting or as ACCOUNT_ID setting for the player '%s' in"
            " the BRIGHTCOVE_PLAYER setting"
            % player)

    context['video_id'] = video_id
    context['player_id'] = player.get('PLAYERID', 'default')
    context['application_id'] = player.get('APPLICATION_ID', None)
    context['embed_id'] = player.get('EMBED_ID', 'default')
    # Use default IFrame embed or "advanced" in-page VIDEO embed?
    context['use_advanced_embed'] = kwargs.get('advanced', False)
    context['width'] = kwargs.get('width', 480)
    context['height'] = kwargs.get('height', 270)
    if 'isUI' in kwargs:
        context['show_controls'] = kwargs['isUI']  # Backwards-compatible
    context['show_controls'] = kwargs.get('show_controls', True)
    return context
